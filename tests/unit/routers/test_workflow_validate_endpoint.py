"""Tests for the workflow validate endpoint + PUT wiring (Phase 110-03).

New endpoint under test:
  - POST /workflows/templates/{id}/validate

Plus the B-1 wave-3 wiring of ``validate_workflow_graph`` into Plan 02's
existing PUT /workflows/templates/{id} handler:
  - Invalid graph body must return 400 BEFORE ``save_template_version()``
    runs (mock-assertion-driven, not just response body).
  - Valid graph body must proceed through ``save_template_version()`` as
    normal.

Test conventions mirror Plan 02's ``test_workflow_save_endpoint.py``:
mount only the workflows router on a fresh FastAPI app, override
``get_current_user_id`` via ``app.dependency_overrides``, patch
``get_workflow_engine`` and the template_versions helpers per-test.
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

# ---------- Fixtures --------------------------------------------------------


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


@pytest.fixture(autouse=True)
def _disable_rate_limiter():
    """Disable slowapi rate limiting so the decorator does not gate requests."""
    from app.middleware.rate_limiter import limiter

    limiter.enabled = False
    yield
    limiter.enabled = True


# ---------- Sample data -----------------------------------------------------


_USER = "user-test"
_OWNED_TEMPLATE_ID = "tmpl-owned"
_SEED_TEMPLATE_ID = "tmpl-seed"
_OTHER_USER_TEMPLATE_ID = "tmpl-other"
_CURRENT_SAVED_AT = "2026-05-11T19:30:00.000000+00:00"
_QUOTED_CURRENT = f'"{_CURRENT_SAVED_AT}"'


_VALID_NODES = [
    {"id": "t1", "kind": "trigger", "label": "Start"},
    {
        "id": "a1",
        "kind": "agent-action",
        "label": "Run",
        "config": {"tool_name": "noop"},
    },
    {"id": "o1", "kind": "output", "label": "Done"},
]
_VALID_EDGES = [
    {"id": "e1", "source": "t1", "target": "a1"},
    {"id": "e2", "source": "a1", "target": "o1"},
]
_VALID_BODY = {"graph_nodes": _VALID_NODES, "graph_edges": _VALID_EDGES}

# A cycle: t1 -> a1 -> a2 -> a1 (a1 and a2 in cycle). a2 -> o1 for rule 6.
_CYCLE_NODES = [
    {"id": "t1", "kind": "trigger", "label": "Start"},
    {
        "id": "a1",
        "kind": "agent-action",
        "label": "A1",
        "config": {"tool_name": "noop"},
    },
    {
        "id": "a2",
        "kind": "agent-action",
        "label": "A2",
        "config": {"tool_name": "noop"},
    },
    {"id": "o1", "kind": "output", "label": "End"},
]
_CYCLE_EDGES = [
    {"id": "e1", "source": "t1", "target": "a1"},
    {"id": "e2", "source": "a1", "target": "a2"},
    {"id": "e3", "source": "a2", "target": "a1"},
    {"id": "e4", "source": "a2", "target": "o1"},
]
_CYCLE_BODY = {"graph_nodes": _CYCLE_NODES, "graph_edges": _CYCLE_EDGES}


_VALID_LAYOUT = {
    "t1": {"x": 0, "y": 0},
    "a1": {"x": 100, "y": 0},
    "o1": {"x": 200, "y": 0},
}
_VALID_SAVE_BODY = {
    "graph_nodes": _VALID_NODES,
    "graph_edges": _VALID_EDGES,
    "graph_layout": _VALID_LAYOUT,
    "comment": "test",
}
_CYCLE_SAVE_BODY = {
    "graph_nodes": _CYCLE_NODES,
    "graph_edges": _CYCLE_EDGES,
    "graph_layout": None,
    "comment": "test",
}


def _owned_template_row() -> dict:
    return {
        "id": _OWNED_TEMPLATE_ID,
        "name": "Owned Template",
        "description": "desc",
        "category": "custom",
        "template_key": None,
        "version": 1,
        "lifecycle_status": "draft",
        "is_generated": False,
        "personas_allowed": None,
        "published_at": None,
        "graph_nodes": _VALID_NODES,
        "graph_edges": _VALID_EDGES,
        "graph_layout": _VALID_LAYOUT,
        "created_by": _USER,
        "current_version_id": "ver-current",
        "updated_at": _CURRENT_SAVED_AT,
    }


def _seed_template_row() -> dict:
    return {
        **_owned_template_row(),
        "id": _SEED_TEMPLATE_ID,
        "name": "Seed",
        "created_by": None,
    }


def _other_user_template_row() -> dict:
    return {
        **_owned_template_row(),
        "id": _OTHER_USER_TEMPLATE_ID,
        "created_by": "user-other",
    }


def _new_version_pydantic():
    """Construct a fresh WorkflowTemplateVersion for save_template_version mocks."""
    from app.workflows.template_versions import WorkflowTemplateVersion

    return WorkflowTemplateVersion(
        id="ver-new",
        template_id=_OWNED_TEMPLATE_ID,
        version_number=2,
        parent_version_id="ver-current",
        graph_nodes=_VALID_NODES,
        graph_edges=_VALID_EDGES,
        graph_layout=_VALID_LAYOUT,
        saved_by_user_id=_USER,
        saved_at="2026-05-11T20:00:00.000000+00:00",
        comment="test",
    )


# ---------- POST /validate: happy paths -------------------------------------


def test_validate_endpoint_valid_graph_returns_empty_errors(client: TestClient):
    """POST with a valid linear graph returns 200 with empty errors list."""
    engine = MagicMock()
    engine.get_template = AsyncMock(return_value=_owned_template_row())

    with patch(
        "app.routers.workflows.get_workflow_engine", return_value=engine
    ):
        response = client.post(
            f"/workflows/templates/{_OWNED_TEMPLATE_ID}/validate",
            json=_VALID_BODY,
        )

    assert response.status_code == 200
    body = response.json()
    assert body == {"errors": []}


def test_validate_endpoint_cycle_returns_errors(client: TestClient):
    """POST with a cycle returns 200 with non-empty errors (rule=3)."""
    engine = MagicMock()
    engine.get_template = AsyncMock(return_value=_owned_template_row())

    with patch(
        "app.routers.workflows.get_workflow_engine", return_value=engine
    ):
        response = client.post(
            f"/workflows/templates/{_OWNED_TEMPLATE_ID}/validate",
            json=_CYCLE_BODY,
        )

    assert response.status_code == 200
    body = response.json()
    assert "errors" in body
    assert len(body["errors"]) >= 2
    rules = {e["rule"] for e in body["errors"]}
    assert 3 in rules


def test_validate_endpoint_no_trigger_returns_rule1_error(client: TestClient):
    """POST with no trigger node returns rule-1 error with node_id=None."""
    engine = MagicMock()
    engine.get_template = AsyncMock(return_value=_owned_template_row())
    body = {
        "graph_nodes": [
            {
                "id": "a1",
                "kind": "agent-action",
                "label": "A",
                "config": {"tool_name": "x"},
            },
            {"id": "o1", "kind": "output", "label": "O"},
        ],
        "graph_edges": [{"id": "e1", "source": "a1", "target": "o1"}],
    }

    with patch(
        "app.routers.workflows.get_workflow_engine", return_value=engine
    ):
        response = client.post(
            f"/workflows/templates/{_OWNED_TEMPLATE_ID}/validate", json=body
        )

    assert response.status_code == 200
    errs = response.json()["errors"]
    rule1 = [e for e in errs if e["rule"] == 1]
    assert len(rule1) == 1
    assert rule1[0]["node_id"] is None


# ---------- POST /validate: auth & scoping ----------------------------------


def test_validate_endpoint_seed_template_passes_for_any_user(client: TestClient):
    """Seed templates (created_by IS NULL) are globally readable - POST OK."""
    engine = MagicMock()
    engine.get_template = AsyncMock(return_value=_seed_template_row())

    with patch(
        "app.routers.workflows.get_workflow_engine", return_value=engine
    ):
        response = client.post(
            f"/workflows/templates/{_SEED_TEMPLATE_ID}/validate",
            json=_VALID_BODY,
        )

    assert response.status_code == 200


def test_validate_endpoint_other_user_template_returns_403(client: TestClient):
    """POST against a template owned by another user -> 403."""
    engine = MagicMock()
    engine.get_template = AsyncMock(return_value=_other_user_template_row())

    with patch(
        "app.routers.workflows.get_workflow_engine", return_value=engine
    ):
        response = client.post(
            f"/workflows/templates/{_OTHER_USER_TEMPLATE_ID}/validate",
            json=_VALID_BODY,
        )

    assert response.status_code == 403


def test_validate_endpoint_missing_template_returns_404(client: TestClient):
    """POST against a non-existent template -> 404."""
    engine = MagicMock()
    engine.get_template = AsyncMock(return_value={"error": "Template not found"})

    with patch(
        "app.routers.workflows.get_workflow_engine", return_value=engine
    ):
        response = client.post(
            "/workflows/templates/no-such-id/validate", json=_VALID_BODY
        )

    assert response.status_code == 404


# ---------- POST /validate: request body validation -------------------------


def test_validate_endpoint_missing_graph_nodes_returns_422(client: TestClient):
    """Pydantic enforcement: missing graph_nodes -> 422."""
    response = client.post(
        f"/workflows/templates/{_OWNED_TEMPLATE_ID}/validate",
        json={"graph_edges": []},  # no graph_nodes
    )
    assert response.status_code == 422


def test_validate_endpoint_invalid_node_kind_returns_422(client: TestClient):
    """Pydantic Literal: bogus node kind -> 422 before validator runs."""
    body = {
        "graph_nodes": [{"id": "x", "kind": "INVALID_KIND", "label": "x"}],
        "graph_edges": [],
    }
    response = client.post(
        f"/workflows/templates/{_OWNED_TEMPLATE_ID}/validate", json=body
    )
    assert response.status_code == 422


# ---------- POST /validate: no DB write -------------------------------------


def test_validate_endpoint_does_not_call_save_template_version(
    client: TestClient,
):
    """POST /validate is read-only: save_template_version is NEVER invoked."""
    engine = MagicMock()
    engine.get_template = AsyncMock(return_value=_owned_template_row())
    save_mock = AsyncMock(return_value=_new_version_pydantic())

    with patch(
        "app.routers.workflows.get_workflow_engine", return_value=engine
    ), patch(
        "app.routers.workflows.save_template_version", new=save_mock
    ):
        response = client.post(
            f"/workflows/templates/{_OWNED_TEMPLATE_ID}/validate",
            json=_VALID_BODY,
        )

    assert response.status_code == 200
    save_mock.assert_not_awaited()
    save_mock.assert_not_called()


# ---------- B-1 wave-3 wiring: PUT calls validate_workflow_graph ------------


def test_put_with_invalid_graph_returns_400_and_skips_save(client: TestClient):
    """B-1 wave-3: PUT with a cycle returns 400 BEFORE save_template_version runs.

    Asserts save_template_version mock was NEVER awaited - the validator
    short-circuits the PUT path before any DB write.
    """
    engine = MagicMock()
    engine.get_template = AsyncMock(return_value=_owned_template_row())
    save_mock = AsyncMock(return_value=_new_version_pydantic())

    with patch(
        "app.routers.workflows.get_workflow_engine", return_value=engine
    ), patch(
        "app.routers.workflows._fetch_current_version_saved_at",
        new=AsyncMock(return_value=_CURRENT_SAVED_AT),
    ), patch(
        "app.routers.workflows.save_template_version", new=save_mock
    ):
        response = client.put(
            f"/workflows/templates/{_OWNED_TEMPLATE_ID}",
            json=_CYCLE_SAVE_BODY,
            headers={"If-Match": _QUOTED_CURRENT},
        )

    assert response.status_code == 400
    body = response.json()
    # Detail carries validation_failed + errors list (Phase 110 wiring contract)
    detail = body.get("detail", body)
    assert isinstance(detail, dict)
    assert detail.get("error") == "validation_failed"
    assert "errors" in detail
    assert len(detail["errors"]) >= 2
    rules = {e["rule"] for e in detail["errors"]}
    assert 3 in rules

    # The B-1 contract: save_template_version was NEVER called
    save_mock.assert_not_awaited()
    save_mock.assert_not_called()


def test_put_with_valid_graph_proceeds_to_save(client: TestClient):
    """B-1 wave-3: PUT with a valid linear graph proceeds normally.

    Asserts save_template_version mock was awaited exactly once - validation
    passes silently and does not interfere with the existing Plan 02 flow.
    """
    engine = MagicMock()
    engine.get_template = AsyncMock(return_value=_owned_template_row())
    save_mock = AsyncMock(return_value=_new_version_pydantic())

    with patch(
        "app.routers.workflows.get_workflow_engine", return_value=engine
    ), patch(
        "app.routers.workflows._fetch_current_version_saved_at",
        new=AsyncMock(return_value=_CURRENT_SAVED_AT),
    ), patch(
        "app.routers.workflows.save_template_version", new=save_mock
    ):
        response = client.put(
            f"/workflows/templates/{_OWNED_TEMPLATE_ID}",
            json=_VALID_SAVE_BODY,
            headers={"If-Match": _QUOTED_CURRENT},
        )

    assert response.status_code == 200
    save_mock.assert_awaited_once()


def test_put_with_no_output_node_returns_400_and_skips_save(client: TestClient):
    """B-1 wave-3: rule-6 violation (no output) also blocks save."""
    engine = MagicMock()
    engine.get_template = AsyncMock(return_value=_owned_template_row())
    save_mock = AsyncMock(return_value=_new_version_pydantic())

    no_output_body = {
        "graph_nodes": [
            {"id": "t1", "kind": "trigger", "label": "T"},
            {
                "id": "a1",
                "kind": "agent-action",
                "label": "A",
                "config": {"tool_name": "x"},
            },
        ],
        "graph_edges": [{"id": "e1", "source": "t1", "target": "a1"}],
    }

    with patch(
        "app.routers.workflows.get_workflow_engine", return_value=engine
    ), patch(
        "app.routers.workflows._fetch_current_version_saved_at",
        new=AsyncMock(return_value=_CURRENT_SAVED_AT),
    ), patch(
        "app.routers.workflows.save_template_version", new=save_mock
    ):
        response = client.put(
            f"/workflows/templates/{_OWNED_TEMPLATE_ID}",
            json=no_output_body,
            headers={"If-Match": _QUOTED_CURRENT},
        )

    assert response.status_code == 400
    detail = response.json().get("detail", {})
    rules = {e["rule"] for e in detail.get("errors", [])}
    assert 6 in rules
    save_mock.assert_not_awaited()
