"""Tests for the workflow template Save / History / Revert endpoints
(Phase 110-02).

New endpoints under test:
  - PUT  /workflows/templates/{template_id}                       (Save)
  - GET  /workflows/templates/{template_id}/history               (Version list)
  - POST /workflows/templates/{template_id}/revert/{version_id}   (Revert)

Plus the ETag header widening on:
  - GET  /workflows/templates/{template_id}

Coverage (B-2 wire format + W-4 SeedForkResponse + auth/scope + validation):
  ETag format
    - GET emits ETag header with quoted ISO8601 saved_at when current_version_id
      is non-NULL.
    - GET falls back to quoted updated_at when current_version_id is NULL
      (legacy / unsaved templates).
  PUT save flow
    - Missing If-Match → 428 Precondition Required.
    - Matching If-Match → 200 with body {version, etag}. Both ETag header and
      body.etag are the quoted ISO8601 string of the new saved_at (B-2).
    - Stripped-quotes If-Match → 200 (defensive parse — B-2).
    - Quoted If-Match → 200 (canonical — B-2).
    - Stale If-Match → 412 with body {..., etag: <fresh quoted ISO8601>} and
      ETag response header matching body.etag (B-2 parity).
    - PUT against seed template (created_by IS NULL) → 409 with exactly four
      keys: error, copied_template_id, seed_name, message (W-4 contract).
    - PUT against template owned by different user → 403.
    - PUT against missing template → 404.
    - Request body validation: missing graph_nodes → 422; invalid node kind → 422.

Tests follow the Phase 109-02 pattern: mount only the workflows router on a
fresh FastAPI app, override get_current_user_id via app.dependency_overrides,
patch get_workflow_engine and the template_versions helpers per-test.
"""

# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

from __future__ import annotations

import re
from collections.abc import Iterator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routers.workflows import get_current_user_id
from app.routers.workflows import router as workflows_router

# Pattern: a quoted ISO8601 datetime (literal double-quotes around the inner
# ISO timestamp). Mirrors the regex used by tests/integration/test_etag_round_trip.py.
QUOTED_ISO8601 = re.compile(r'^"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[\d.+:Z-]*"$')


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
_CURRENT_VERSION_ID = "ver-current"
_CURRENT_SAVED_AT = "2026-05-11T19:30:00.000000+00:00"
_QUOTED_CURRENT = f'"{_CURRENT_SAVED_AT}"'

_NEW_SAVED_AT = "2026-05-11T20:00:00.000000+00:00"
_QUOTED_NEW = f'"{_NEW_SAVED_AT}"'

_SAMPLE_NODES = [
    {"id": "trigger", "kind": "trigger", "label": "Start"},
    {"id": "out", "kind": "output", "label": "End"},
]
_SAMPLE_EDGES = [{"id": "e0", "source": "trigger", "target": "out"}]
_SAMPLE_LAYOUT = {
    "trigger": {"x": 0, "y": 0},
    "out": {"x": 200, "y": 0},
}

_VALID_REQUEST_BODY = {
    "graph_nodes": _SAMPLE_NODES,
    "graph_edges": _SAMPLE_EDGES,
    "graph_layout": _SAMPLE_LAYOUT,
    "comment": "test save",
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
        "graph_nodes": _SAMPLE_NODES,
        "graph_edges": _SAMPLE_EDGES,
        "graph_layout": _SAMPLE_LAYOUT,
        "created_by": _USER,
        "current_version_id": _CURRENT_VERSION_ID,
        "updated_at": _CURRENT_SAVED_AT,
    }


def _seed_template_row() -> dict:
    return {
        **_owned_template_row(),
        "id": _SEED_TEMPLATE_ID,
        "name": "Seeded Template",
        "created_by": None,
    }


def _other_user_template_row() -> dict:
    return {
        **_owned_template_row(),
        "id": _OTHER_USER_TEMPLATE_ID,
        "created_by": "user-other",
    }


def _current_version_row() -> dict:
    return {
        "id": _CURRENT_VERSION_ID,
        "template_id": _OWNED_TEMPLATE_ID,
        "version_number": 1,
        "parent_version_id": None,
        "graph_nodes": _SAMPLE_NODES,
        "graph_edges": _SAMPLE_EDGES,
        "graph_layout": _SAMPLE_LAYOUT,
        "saved_by_user_id": _USER,
        "saved_at": _CURRENT_SAVED_AT,
        "comment": "v1",
    }


def _new_version_row() -> dict:
    return {
        **_current_version_row(),
        "id": "ver-new",
        "version_number": 2,
        "parent_version_id": _CURRENT_VERSION_ID,
        "saved_at": _NEW_SAVED_AT,
        "comment": "test save",
    }


# ---------- ETag header on GET ----------------------------------------------


def test_get_template_emits_etag_header_with_quoted_iso8601(client: TestClient):
    """GET /workflows/templates/{id} response has ETag header in quoted ISO8601."""
    engine = MagicMock()
    engine.get_template = AsyncMock(return_value=_owned_template_row())
    version = _current_version_row()

    with patch(
        "app.routers.workflows.get_workflow_engine", return_value=engine
    ), patch(
        "app.routers.workflows._fetch_current_version_saved_at",
        new=AsyncMock(return_value=version["saved_at"]),
    ):
        response = client.get(f"/workflows/templates/{_OWNED_TEMPLATE_ID}")

    assert response.status_code == 200
    assert "etag" in {k.lower() for k in response.headers.keys()}
    etag = response.headers["etag"]
    assert QUOTED_ISO8601.match(etag), f"ETag not quoted ISO8601: {etag!r}"
    assert _CURRENT_SAVED_AT in etag


def test_get_template_etag_falls_back_to_updated_at_when_no_current_version(
    client: TestClient,
):
    """Legacy templates with current_version_id IS NULL fall back to quoted updated_at."""
    row = _owned_template_row()
    row["current_version_id"] = None  # legacy / unsaved
    row["updated_at"] = "2026-05-11T15:00:00.000000+00:00"

    engine = MagicMock()
    engine.get_template = AsyncMock(return_value=row)

    with patch(
        "app.routers.workflows.get_workflow_engine", return_value=engine
    ), patch(
        "app.routers.workflows._fetch_current_version_saved_at",
        new=AsyncMock(return_value=None),
    ):
        response = client.get(f"/workflows/templates/{_OWNED_TEMPLATE_ID}")

    assert response.status_code == 200
    etag = response.headers["etag"]
    assert QUOTED_ISO8601.match(etag)
    assert row["updated_at"] in etag


# ---------- PUT save flow ---------------------------------------------------


def test_put_template_missing_if_match_returns_428(client: TestClient):
    """PUT without If-Match → 428 Precondition Required."""
    engine = MagicMock()
    engine.get_template = AsyncMock(return_value=_owned_template_row())

    with patch("app.routers.workflows.get_workflow_engine", return_value=engine):
        response = client.put(
            f"/workflows/templates/{_OWNED_TEMPLATE_ID}",
            json=_VALID_REQUEST_BODY,
        )

    assert response.status_code == 428


def test_put_template_matching_if_match_returns_200_with_body_etag(
    client: TestClient,
):
    """PUT with matching If-Match returns 200 with body containing the new ETag."""
    engine = MagicMock()
    engine.get_template = AsyncMock(return_value=_owned_template_row())

    new_version = _new_version_row()

    with patch(
        "app.routers.workflows.get_workflow_engine", return_value=engine
    ), patch(
        "app.routers.workflows._fetch_current_version_saved_at",
        new=AsyncMock(return_value=_CURRENT_SAVED_AT),
    ), patch(
        "app.routers.workflows.save_template_version",
        new=AsyncMock(return_value=_pydantic_version(new_version)),
    ):
        response = client.put(
            f"/workflows/templates/{_OWNED_TEMPLATE_ID}",
            json=_VALID_REQUEST_BODY,
            headers={"If-Match": _QUOTED_CURRENT},
        )

    assert response.status_code == 200
    body = response.json()
    assert "version" in body
    assert "etag" in body
    # body.etag is the canonical wire format — quoted ISO8601 of new saved_at
    assert body["etag"] == _QUOTED_NEW
    assert QUOTED_ISO8601.match(body["etag"])
    # ETag header echoes body.etag
    assert response.headers["etag"] == body["etag"]


def test_put_template_stripped_quotes_if_match_succeeds_defensively(
    client: TestClient,
):
    """Defensive: PUT with unquoted If-Match still parses correctly (B-2)."""
    engine = MagicMock()
    engine.get_template = AsyncMock(return_value=_owned_template_row())
    new_version = _new_version_row()

    with patch(
        "app.routers.workflows.get_workflow_engine", return_value=engine
    ), patch(
        "app.routers.workflows._fetch_current_version_saved_at",
        new=AsyncMock(return_value=_CURRENT_SAVED_AT),
    ), patch(
        "app.routers.workflows.save_template_version",
        new=AsyncMock(return_value=_pydantic_version(new_version)),
    ):
        response = client.put(
            f"/workflows/templates/{_OWNED_TEMPLATE_ID}",
            json=_VALID_REQUEST_BODY,
            headers={"If-Match": _CURRENT_SAVED_AT},  # NO surrounding quotes
        )

    assert response.status_code == 200


def test_put_template_quoted_if_match_succeeds_canonical(client: TestClient):
    """Canonical: PUT with quoted If-Match succeeds (matches the wire format)."""
    engine = MagicMock()
    engine.get_template = AsyncMock(return_value=_owned_template_row())
    new_version = _new_version_row()

    with patch(
        "app.routers.workflows.get_workflow_engine", return_value=engine
    ), patch(
        "app.routers.workflows._fetch_current_version_saved_at",
        new=AsyncMock(return_value=_CURRENT_SAVED_AT),
    ), patch(
        "app.routers.workflows.save_template_version",
        new=AsyncMock(return_value=_pydantic_version(new_version)),
    ):
        response = client.put(
            f"/workflows/templates/{_OWNED_TEMPLATE_ID}",
            json=_VALID_REQUEST_BODY,
            headers={"If-Match": _QUOTED_CURRENT},
        )

    assert response.status_code == 200


def test_put_template_stale_if_match_returns_412_with_etag_in_body_and_header(
    client: TestClient,
):
    """B-2: PUT with stale If-Match returns 412; fresh ETag in BOTH header AND body.etag."""
    engine = MagicMock()
    engine.get_template = AsyncMock(return_value=_owned_template_row())

    # save_template_version returns None → stale write
    with patch(
        "app.routers.workflows.get_workflow_engine", return_value=engine
    ), patch(
        "app.routers.workflows._fetch_current_version_saved_at",
        new=AsyncMock(return_value=_CURRENT_SAVED_AT),
    ), patch(
        "app.routers.workflows.save_template_version",
        new=AsyncMock(return_value=None),  # stale signal
    ):
        response = client.put(
            f"/workflows/templates/{_OWNED_TEMPLATE_ID}",
            json=_VALID_REQUEST_BODY,
            headers={"If-Match": '"2026-05-11T18:00:00.000000+00:00"'},  # stale
        )

    assert response.status_code == 412
    body = response.json()
    # B-2: etag in body
    assert "etag" in body
    assert QUOTED_ISO8601.match(body["etag"])
    assert body["etag"] == _QUOTED_CURRENT
    # B-2 parity: header matches body
    assert response.headers["etag"] == body["etag"]


def test_put_template_seed_returns_409_with_all_four_keys(client: TestClient):
    """W-4: PUT on a seed (created_by IS NULL) returns 409 with exact body shape."""
    engine = MagicMock()
    engine.get_template = AsyncMock(return_value=_seed_template_row())

    with patch(
        "app.routers.workflows.get_workflow_engine", return_value=engine
    ), patch(
        "app.routers.workflows.copy_seed_template_for_user",
        new=AsyncMock(
            return_value={
                "copied_template_id": "new-copy-id",
                "seed_name": "Seeded Template",
            }
        ),
    ):
        response = client.put(
            f"/workflows/templates/{_SEED_TEMPLATE_ID}",
            json=_VALID_REQUEST_BODY,
            headers={"If-Match": _QUOTED_CURRENT},
        )

    assert response.status_code == 409
    body = response.json()
    # W-4: EXACT 4-key shape (error, copied_template_id, seed_name, message)
    assert set(body.keys()) == {"error", "copied_template_id", "seed_name", "message"}
    assert body["error"] == "seed_template_immutable"
    assert body["copied_template_id"] == "new-copy-id"
    assert body["seed_name"] == "Seeded Template"
    assert isinstance(body["message"], str) and len(body["message"]) > 0


def test_put_template_owned_by_other_user_returns_403(client: TestClient):
    """PUT against a template owned by a different user → 403."""
    engine = MagicMock()
    engine.get_template = AsyncMock(return_value=_other_user_template_row())

    with patch("app.routers.workflows.get_workflow_engine", return_value=engine):
        response = client.put(
            f"/workflows/templates/{_OTHER_USER_TEMPLATE_ID}",
            json=_VALID_REQUEST_BODY,
            headers={"If-Match": _QUOTED_CURRENT},
        )

    assert response.status_code == 403


def test_put_template_missing_returns_404(client: TestClient):
    """PUT against a non-existent template → 404."""
    engine = MagicMock()
    engine.get_template = AsyncMock(return_value={"error": "Template not found"})

    with patch("app.routers.workflows.get_workflow_engine", return_value=engine):
        response = client.put(
            "/workflows/templates/no-such-id",
            json=_VALID_REQUEST_BODY,
            headers={"If-Match": _QUOTED_CURRENT},
        )

    assert response.status_code == 404


def test_put_template_missing_graph_nodes_returns_422(client: TestClient):
    """Pydantic validation: missing graph_nodes → 422."""
    response = client.put(
        f"/workflows/templates/{_OWNED_TEMPLATE_ID}",
        json={"graph_edges": []},  # no graph_nodes
        headers={"If-Match": _QUOTED_CURRENT},
    )
    assert response.status_code == 422


def test_put_template_invalid_node_kind_returns_422(client: TestClient):
    """Pydantic Literal enforcement: bogus node kind → 422."""
    bad_body = {
        "graph_nodes": [{"id": "x", "kind": "INVALID_KIND", "label": "x"}],
        "graph_edges": [],
        "graph_layout": None,
    }
    response = client.put(
        f"/workflows/templates/{_OWNED_TEMPLATE_ID}",
        json=bad_body,
        headers={"If-Match": _QUOTED_CURRENT},
    )
    assert response.status_code == 422


# ---------- GET /history ----------------------------------------------------


def test_get_template_history_returns_versions_desc(client: TestClient):
    """GET /history returns ordered HistoryItem list."""
    engine = MagicMock()
    engine.get_template = AsyncMock(return_value=_owned_template_row())

    from app.workflows.template_versions import HistoryItem

    history = [
        HistoryItem(
            version_number=2,
            version_id="ver-2",
            saved_at=_NEW_SAVED_AT,
            saved_by_user_id=_USER,
            saved_by_user_name=None,
            comment="newer",
        ),
        HistoryItem(
            version_number=1,
            version_id="ver-1",
            saved_at=_CURRENT_SAVED_AT,
            saved_by_user_id=_USER,
            saved_by_user_name=None,
            comment="v1",
        ),
    ]

    with patch(
        "app.routers.workflows.get_workflow_engine", return_value=engine
    ), patch(
        "app.routers.workflows.list_template_history",
        new=AsyncMock(return_value=history),
    ):
        response = client.get(f"/workflows/templates/{_OWNED_TEMPLATE_ID}/history")

    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)
    assert len(body) == 2
    assert body[0]["version_number"] == 2
    assert body[1]["version_number"] == 1


# ---------- POST /revert ----------------------------------------------------


def test_post_revert_returns_new_version_with_etag(client: TestClient):
    """POST /revert/{version_id} returns the new version + body.etag."""
    engine = MagicMock()
    engine.get_template = AsyncMock(return_value=_owned_template_row())

    new_version = _new_version_row()
    new_version["parent_version_id"] = _CURRENT_VERSION_ID

    with patch(
        "app.routers.workflows.get_workflow_engine", return_value=engine
    ), patch(
        "app.routers.workflows._fetch_current_version_saved_at",
        new=AsyncMock(return_value=_CURRENT_SAVED_AT),
    ), patch(
        "app.routers.workflows.revert_template_to_version",
        new=AsyncMock(return_value=_pydantic_version(new_version)),
    ):
        response = client.post(
            f"/workflows/templates/{_OWNED_TEMPLATE_ID}/revert/{_CURRENT_VERSION_ID}",
            headers={"If-Match": _QUOTED_CURRENT},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["etag"] == _QUOTED_NEW
    assert body["version"]["parent_version_id"] == _CURRENT_VERSION_ID
    assert response.headers["etag"] == body["etag"]


def test_post_revert_stale_if_match_returns_412(client: TestClient):
    """POST /revert with stale If-Match → 412 with fresh etag (B-2 parity)."""
    engine = MagicMock()
    engine.get_template = AsyncMock(return_value=_owned_template_row())

    with patch(
        "app.routers.workflows.get_workflow_engine", return_value=engine
    ), patch(
        "app.routers.workflows._fetch_current_version_saved_at",
        new=AsyncMock(return_value=_CURRENT_SAVED_AT),
    ), patch(
        "app.routers.workflows.revert_template_to_version",
        new=AsyncMock(return_value=None),
    ):
        response = client.post(
            f"/workflows/templates/{_OWNED_TEMPLATE_ID}/revert/{_CURRENT_VERSION_ID}",
            headers={"If-Match": '"2026-05-11T18:00:00.000000+00:00"'},  # stale
        )

    assert response.status_code == 412
    body = response.json()
    assert "etag" in body
    assert QUOTED_ISO8601.match(body["etag"])
    assert response.headers["etag"] == body["etag"]


# ---------- Helpers ---------------------------------------------------------


def _pydantic_version(row: dict):
    from app.workflows.template_versions import WorkflowTemplateVersion

    return WorkflowTemplateVersion(**row)
