"""End-to-end editor round-trip — I-4 close-out for Phase 110.

Drag node → save → reload → verify node persists. Uses FastAPI TestClient on
the backend to simulate what the editor consumer would do, without spinning
up a real browser. Covers ROADMAP criterion #1 at the API layer:

    "A user can drag a node from a left-rail palette onto the canvas, connect
    it to existing nodes by dragging from one node's output handle to
    another's input handle, click the new node to open a right-side
    properties drawer, edit the node's `label` and per-kind `config` fields
    via a Zod-driven form, and click Save — the canvas state persists to the
    backend and survives a page reload"

The drag/connect/configure happens in the React layer (covered by Plan 04's
vitest suite). What this file owns is the API-side round-trip: the editor's
final state (graph_nodes + graph_edges + graph_layout) is preserved through
PUT and re-readable via GET with the new graph values present.

Run requirements
----------------
    supabase start
    supabase db reset --local         # apply Phase 109 + 110 migrations
    export SUPABASE_URL=...
    export SUPABASE_SERVICE_ROLE_KEY=...
    uv run pytest tests/integration/test_editor_save_reload_round_trip.py -v

Without those env vars the suite SKIPS cleanly.

Tests SKIP cleanly on workstations without Supabase creds.
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

QUOTED_ISO8601 = re.compile(r'^"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[\d.+:Z-]*"$')


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def client() -> Iterator[Any]:
    """Return a FastAPI TestClient mounted on the workflows router.

    Uses dependency_overrides to bypass real auth — every request is treated
    as user-id ``editor-roundtrip-user``.
    """
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from app.routers.workflows import get_current_user_id
    from app.routers.workflows import router as workflows_router

    app = FastAPI()

    async def _fake_user() -> str:
        return "editor-roundtrip-user"

    app.dependency_overrides[get_current_user_id] = _fake_user
    app.include_router(workflows_router)

    from app.middleware.rate_limiter import limiter

    prev_enabled = limiter.enabled
    limiter.enabled = False
    try:
        with TestClient(app) as c:
            yield c
    finally:
        limiter.enabled = prev_enabled


@pytest.fixture()
def fixture_template() -> Iterator[dict[str, Any]]:
    """Insert a private template owned by the test user; yield its id; clean up.

    A fresh template per test so version_number assertions are deterministic.
    """
    from app.services.supabase_client import get_client

    db = get_client()
    template_row = {
        "name": "Editor Round-Trip Fixture",
        "description": (
            "Created by tests/integration/test_editor_save_reload_round_trip.py"
        ),
        "category": "test-fixture",
        "lifecycle_status": "draft",
        "created_by": "editor-roundtrip-user",
        "graph_nodes": [
            {"id": "trigger", "kind": "trigger", "label": "Start"},
            {"id": "out", "kind": "output", "label": "End"},
        ],
        "graph_edges": [{"id": "e0", "source": "trigger", "target": "out"}],
        "graph_layout": {
            "trigger": {"x": 0, "y": 0},
            "out": {"x": 200, "y": 0},
        },
    }
    inserted = db.table("workflow_templates").insert(template_row).execute()
    template = inserted.data[0]
    template_id = template["id"]

    # Bootstrap a v1 row so current_version_id is set + ETag is non-null.
    rpc_res = db.rpc(
        "save_workflow_template_version",
        {
            "p_template_id": template_id,
            "p_user_id": "editor-roundtrip-user",
            "p_graph_nodes": template_row["graph_nodes"],
            "p_graph_edges": template_row["graph_edges"],
            "p_graph_layout": template_row["graph_layout"],
            "p_comment": "v1 bootstrap (editor round-trip fixture)",
            "p_if_match_saved_at": None,
            "p_parent_version_id": None,
        },
    ).execute()
    assert rpc_res.data, "Bootstrap v1 version write returned no rows"

    yield {"id": template_id}

    try:
        db.table("workflow_templates").delete().eq(
            "id", template_id
        ).execute()
    except Exception:
        pass


# ---------------------------------------------------------------------------
# I-4 round-trip tests — ROADMAP criterion #1 end-to-end
# ---------------------------------------------------------------------------


def test_editor_round_trip_save_and_reload_preserves_added_node(
    client: Any, fixture_template: dict[str, Any]
) -> None:
    """Save a graph with a new agent-action node, then GET it back — node persists.

    Steps:
      1. GET /workflows/templates/{id} → capture body + ETag header.
      2. Append a new agent-action node + edge to graph_nodes/edges.
      3. PUT with If-Match = captured ETag, body = mutated graph.
         Assert 200, capture new ETag from response body.
      4. GET /workflows/templates/{id} → reload.
      5. Assert response.graph_nodes contains the appended node by id.
      6. Assert response.graph_edges contains the new edge.
    """
    template_id = fixture_template["id"]

    # 1. Initial GET — capture state + ETag.
    get_res = client.get(f"/workflows/templates/{template_id}")
    assert get_res.status_code == 200, get_res.text
    initial_etag = get_res.headers.get("etag")
    assert initial_etag, "GET response did not include ETag header"
    assert QUOTED_ISO8601.match(initial_etag)
    initial_body = get_res.json()
    assert initial_body.get("graph_nodes") is not None
    initial_nodes = list(initial_body["graph_nodes"])
    initial_edges = list(initial_body.get("graph_edges") or [])

    # 2. Mutate: simulate "drag agent-action node onto canvas + connect".
    new_node = {
        "id": "step-from-drag",
        "kind": "agent-action",
        "label": "Newly dragged step",
        "config": {"tool_name": "send_email"},
    }
    new_edge = {
        "id": "e-from-drag",
        "source": "trigger",
        "target": "step-from-drag",
    }
    mutated_nodes = [*initial_nodes, new_node]
    mutated_edges = [*initial_edges, new_edge]
    mutated_layout = {
        **(initial_body.get("graph_layout") or {}),
        "step-from-drag": {"x": 100, "y": 100},
    }

    # 3. PUT save (simulates "click Save in editor").
    put_res = client.put(
        f"/workflows/templates/{template_id}",
        json={
            "graph_nodes": mutated_nodes,
            "graph_edges": mutated_edges,
            "graph_layout": mutated_layout,
            "comment": "I-4 round-trip test: added drag node",
        },
        headers={"If-Match": initial_etag},
    )
    assert put_res.status_code == 200, put_res.text
    put_body = put_res.json()
    assert "etag" in put_body
    assert "version" in put_body
    new_etag = put_body["etag"]
    assert QUOTED_ISO8601.match(new_etag)
    # B-2: header echoes body
    assert put_res.headers["etag"] == new_etag
    # Version number incremented
    new_version_number = put_body["version"].get("version_number")
    assert new_version_number is not None and new_version_number > 1

    # 4. Reload via GET (simulates "page reload after save").
    reload_res = client.get(f"/workflows/templates/{template_id}")
    assert reload_res.status_code == 200, reload_res.text
    reload_body = reload_res.json()

    # 5+6. Verify the new node + edge survived the round-trip.
    reloaded_nodes = reload_body.get("graph_nodes") or []
    reloaded_edges = reload_body.get("graph_edges") or []
    reloaded_node_ids = {n["id"] for n in reloaded_nodes}
    reloaded_edge_ids = {e["id"] for e in reloaded_edges}
    assert "step-from-drag" in reloaded_node_ids, (
        "Newly added node was not preserved through Save+Reload"
    )
    assert "e-from-drag" in reloaded_edge_ids, (
        "Newly added edge was not preserved through Save+Reload"
    )
    # And the new ETag from PUT matches the reloaded one (next-write parity).
    assert reload_res.headers.get("etag") == new_etag


def test_editor_round_trip_revert_restores_prior_state(
    client: Any, fixture_template: dict[str, Any]
) -> None:
    """Save v2 (modify v1) → revert to v1 → GET → assert v1's graph back.

    Steps:
      1. Capture v1 ETag via GET.
      2. PUT a v2 with an additional node; capture new ETag.
      3. GET /history → find v1's version_id.
      4. POST /revert/{v1_version_id} with If-Match = current etag.
         Assert 200 → version_number = 3 (new revert version).
      5. GET /workflows/templates/{id} → assert graph_nodes matches v1's
         shape (NO 'step-from-drag' node — that was a v2 addition).
      6. Assert /history shows v1, v2, v3.
    """
    template_id = fixture_template["id"]

    # 1. Get v1 ETag + body.
    get_v1 = client.get(f"/workflows/templates/{template_id}")
    assert get_v1.status_code == 200, get_v1.text
    v1_etag = get_v1.headers["etag"]
    v1_body = get_v1.json()
    v1_node_ids = {n["id"] for n in (v1_body.get("graph_nodes") or [])}

    # 2. Save v2 with an extra node.
    extra_node = {
        "id": "v2-only-step",
        "kind": "agent-action",
        "label": "Only present in v2",
        "config": {"tool_name": "noop"},
    }
    v2_nodes = [*(v1_body.get("graph_nodes") or []), extra_node]
    v2_edges = [
        *(v1_body.get("graph_edges") or []),
        {"id": "v2-only-edge", "source": "trigger", "target": "v2-only-step"},
    ]
    put_v2 = client.put(
        f"/workflows/templates/{template_id}",
        json={
            "graph_nodes": v2_nodes,
            "graph_edges": v2_edges,
            "graph_layout": None,
            "comment": "v2 (will be reverted)",
        },
        headers={"If-Match": v1_etag},
    )
    assert put_v2.status_code == 200, put_v2.text
    v2_etag = put_v2.json()["etag"]

    # 3. Find v1's version_id via /history.
    hist_res = client.get(f"/workflows/templates/{template_id}/history")
    assert hist_res.status_code == 200, hist_res.text
    history = hist_res.json()
    assert isinstance(history, list) and len(history) >= 2
    v1_history_row = next(
        (h for h in history if h["version_number"] == 1), None
    )
    assert v1_history_row is not None, "v1 row missing from history"
    v1_version_id = v1_history_row["version_id"]

    # 4. POST revert to v1.
    revert_res = client.post(
        f"/workflows/templates/{template_id}/revert/{v1_version_id}",
        headers={"If-Match": v2_etag},
    )
    assert revert_res.status_code == 200, revert_res.text
    revert_body = revert_res.json()
    assert revert_body["version"]["version_number"] == 3
    assert revert_body["version"]["parent_version_id"] == v1_version_id

    # 5. GET → graph matches v1 (no v2 node).
    reload_res = client.get(f"/workflows/templates/{template_id}")
    assert reload_res.status_code == 200, reload_res.text
    reloaded = reload_res.json()
    reloaded_node_ids = {
        n["id"] for n in (reloaded.get("graph_nodes") or [])
    }
    assert reloaded_node_ids == v1_node_ids, (
        f"After revert, reloaded nodes {reloaded_node_ids} != v1 nodes "
        f"{v1_node_ids}"
    )
    assert "v2-only-step" not in reloaded_node_ids

    # 6. History now shows v1, v2, v3.
    hist2_res = client.get(
        f"/workflows/templates/{template_id}/history"
    )
    assert hist2_res.status_code == 200, hist2_res.text
    history2 = hist2_res.json()
    version_numbers = sorted({h["version_number"] for h in history2})
    assert 1 in version_numbers
    assert 2 in version_numbers
    assert 3 in version_numbers
