"""ETag wire-format round-trip — B-2 parity tests for Phase 110-02.

Asserts the server's ETag wire format is consistent end-to-end:
  - GET emits ``ETag: "<ISO8601>"`` header (quoted ISO8601).
  - PUT with the captured header value verbatim returns 200 (round-trip OK).
  - PUT with the value stripped of surrounding quotes ALSO returns 200
    (defensive server-side parse).
  - PUT with a mismatched ETag returns 412 with the fresh quoted ETag in
    BOTH the response header AND the response body under the ``etag`` key.

These tests use real Supabase + the FastAPI app (mounted via TestClient
without booting external integrations). They SKIP cleanly when Supabase
creds are absent — matching the rest of tests/integration/.

Run requirements
----------------
    supabase start
    supabase db reset --local         # apply Phase 109 + 110 migrations
    export SUPABASE_URL=...
    export SUPABASE_SERVICE_ROLE_KEY=...
    uv run pytest tests/integration/test_etag_round_trip.py -v

Without those env vars the suite SKIPS cleanly.
"""

# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

from __future__ import annotations

import os
import re
from collections.abc import Iterator
from typing import Any

import pytest

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not all(
            os.environ.get(var)
            for var in ("SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY")
        ),
        reason="Supabase credentials not provided in environment variables.",
    ),
]

# Pattern: a quoted ISO8601 datetime (literal double-quotes around the inner
# ISO timestamp). Mirrors the unit-test regex from
# tests/unit/routers/test_workflow_save_endpoint.py.
QUOTED_ISO8601 = re.compile(r'^"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[\d.+:Z-]*"$')


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def client() -> Iterator[Any]:
    """Return a FastAPI TestClient mounted on the workflows router.

    Uses dependency_overrides to bypass real auth — every request is treated
    as user-id ``etag-test-user``.
    """
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from app.routers.workflows import get_current_user_id
    from app.routers.workflows import router as workflows_router

    app = FastAPI()

    async def _fake_user() -> str:
        return "etag-test-user"

    app.dependency_overrides[get_current_user_id] = _fake_user
    app.include_router(workflows_router)

    # Disable rate limiting for the duration of the module.
    from app.middleware.rate_limiter import limiter

    prev_enabled = limiter.enabled
    limiter.enabled = False
    try:
        with TestClient(app) as c:
            yield c
    finally:
        limiter.enabled = prev_enabled


@pytest.fixture(scope="module")
def fixture_template(client: Any) -> Iterator[dict[str, Any]]:
    """Insert a private template owned by the test user; yield its id; clean up.

    Uses the Supabase service-role client directly to bypass router-level auth
    (the real CREATE flow requires more scaffolding than this ETag suite
    cares about).
    """
    from app.services.supabase_client import get_client

    db = get_client()
    template_row = {
        "name": "ETag Round-Trip Fixture",
        "description": "Created by tests/integration/test_etag_round_trip.py",
        "category": "test-fixture",
        "lifecycle_status": "draft",
        "created_by": "etag-test-user",
        "graph_nodes": [
            {"id": "trigger", "kind": "trigger", "label": "Start"},
            {"id": "out", "kind": "output", "label": "End"},
        ],
        "graph_edges": [{"id": "e0", "source": "trigger", "target": "out"}],
        "graph_layout": {"trigger": {"x": 0, "y": 0}, "out": {"x": 200, "y": 0}},
    }
    inserted = (
        db.table("workflow_templates").insert(template_row).execute()
    )
    template = inserted.data[0]
    template_id = template["id"]

    # Bootstrap a v1 version row via the new RPC so current_version_id is set.
    rpc_res = db.rpc(
        "save_workflow_template_version",
        {
            "p_template_id": template_id,
            "p_user_id": "etag-test-user",
            "p_graph_nodes": template_row["graph_nodes"],
            "p_graph_edges": template_row["graph_edges"],
            "p_graph_layout": template_row["graph_layout"],
            "p_comment": "v1 bootstrap (etag test fixture)",
            "p_if_match_saved_at": None,
            "p_parent_version_id": None,
        },
    ).execute()
    assert rpc_res.data, "Bootstrap v1 version write returned no rows"

    yield {"id": template_id}

    # Cleanup: CASCADE deletes version rows.
    try:
        db.table("workflow_templates").delete().eq("id", template_id).execute()
    except Exception:
        pass


# ---------------------------------------------------------------------------
# B-2 parity tests
# ---------------------------------------------------------------------------


def test_etag_round_trip_get_then_put_matching_returns_200(
    client: Any, fixture_template: dict[str, Any]
):
    """Capture ETag from GET; send it verbatim on PUT; expect 200 + matching etag in body."""
    template_id = fixture_template["id"]

    # 1. GET the template; capture the ETag header.
    get_res = client.get(f"/workflows/templates/{template_id}")
    assert get_res.status_code == 200, get_res.text
    etag = get_res.headers.get("etag")
    assert etag, "GET response did not include an ETag header"
    assert QUOTED_ISO8601.match(etag), f"ETag not quoted ISO8601: {etag!r}"

    # 2. PUT with the captured ETag verbatim.
    body = {
        "graph_nodes": [
            {"id": "trigger", "kind": "trigger", "label": "Start"},
            {"id": "step", "kind": "agent-action", "label": "Edited step"},
            {"id": "out", "kind": "output", "label": "End"},
        ],
        "graph_edges": [
            {"id": "e0", "source": "trigger", "target": "step"},
            {"id": "e1", "source": "step", "target": "out"},
        ],
        "graph_layout": None,
        "comment": "etag round-trip test",
    }
    put_res = client.put(
        f"/workflows/templates/{template_id}",
        json=body,
        headers={"If-Match": etag},
    )
    assert put_res.status_code == 200, put_res.text
    put_body = put_res.json()
    assert "etag" in put_body and "version" in put_body
    assert QUOTED_ISO8601.match(put_body["etag"])
    # B-2: body etag is canonical, header echoes it.
    assert put_res.headers["etag"] == put_body["etag"]


def test_etag_round_trip_put_with_stripped_quotes_succeeds_defensively(
    client: Any, fixture_template: dict[str, Any]
):
    """Server defensively strips surrounding quotes from If-Match — verify."""
    template_id = fixture_template["id"]

    # GET fresh etag for this test (mutates module-scope fixture state).
    get_res = client.get(f"/workflows/templates/{template_id}")
    etag = get_res.headers["etag"]
    assert QUOTED_ISO8601.match(etag)
    stripped = etag[1:-1]  # remove leading + trailing double-quote

    body = {
        "graph_nodes": [
            {"id": "trigger", "kind": "trigger", "label": "Start"},
            {"id": "out", "kind": "output", "label": "End"},
        ],
        "graph_edges": [{"id": "e0", "source": "trigger", "target": "out"}],
        "graph_layout": None,
        "comment": "defensive parse test",
    }
    put_res = client.put(
        f"/workflows/templates/{template_id}",
        json=body,
        headers={"If-Match": stripped},  # NO surrounding quotes
    )
    assert put_res.status_code == 200, put_res.text


def test_etag_round_trip_mismatched_if_match_returns_412_with_quoted_etag_in_body(
    client: Any, fixture_template: dict[str, Any]
):
    """B-2: 412 response body has etag key matching the response header."""
    template_id = fixture_template["id"]

    # Use a deliberately-stale ETag value.
    stale_etag = '"1970-01-01T00:00:00+00:00"'

    body = {
        "graph_nodes": [
            {"id": "trigger", "kind": "trigger", "label": "Start"},
            {"id": "out", "kind": "output", "label": "End"},
        ],
        "graph_edges": [{"id": "e0", "source": "trigger", "target": "out"}],
        "graph_layout": None,
    }
    put_res = client.put(
        f"/workflows/templates/{template_id}",
        json=body,
        headers={"If-Match": stale_etag},
    )
    assert put_res.status_code == 412, put_res.text
    res_body = put_res.json()
    assert "etag" in res_body
    assert QUOTED_ISO8601.match(res_body["etag"])
    # B-2: header matches body
    assert put_res.headers["etag"] == res_body["etag"]


def test_etag_round_trip_missing_if_match_returns_428(
    client: Any, fixture_template: dict[str, Any]
):
    """PUT without If-Match → 428 Precondition Required."""
    template_id = fixture_template["id"]
    body = {"graph_nodes": [], "graph_edges": [], "graph_layout": None}
    put_res = client.put(f"/workflows/templates/{template_id}", json=body)
    assert put_res.status_code == 428
