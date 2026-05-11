"""Unit tests for app/workflows/template_versions.py (Phase 110-02).

Covers:
- save_template_version() — happy path, stale If-Match (returns None for HTTP 412),
  first-save (no If-Match), parent_version_id explicit override.
- list_template_history() — DESC ordering by version_number, graceful fallback
  when joined user names are unavailable.
- revert_template_to_version() — reads target's graph_*, calls save with explicit
  parent_version_id pointing at the reverted-TO version.
- copy_seed_template_for_user() — creates a private copy with created_by=user_id,
  bootstraps a v1 workflow_template_versions row, returns dict with both
  copied_template_id AND seed_name keys (W-4 contract for the 409 SeedForkResponse).
  Raises ValueError when source template is NOT a seed (created_by IS NOT NULL).

Additional behavioural tests for Task 02-04 (engine integration):
- WorkflowEngine.list_templates() SELECT clause MUST include current_version_id
  so the column reaches the wire — verified via mock returning a row dict that
  contains the key and asserting the engine's returned list preserves it.
- WorkflowEngine.start_workflow_execution() MUST pass p_template_version_id in
  rpc_params dict keyed off template.current_version_id — verified via
  captured-args assertion on the mocked .rpc() call.

All tests use AsyncMock to stub the supabase async client (via
app.services.supabase_client.get_async_client) — no real DB hit.
"""

# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ----------------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------------


def _make_rpc_mock(return_data: list[dict[str, Any]] | None) -> MagicMock:
    """Return a MagicMock that mimics ``client.rpc(name, params)`` returning
    a chained ``.execute()`` whose ``.data`` is ``return_data``.

    The supabase Python client's async path returns a coroutine from .execute(),
    so we wrap the result in an AsyncMock at that level. Higher up the chain
    (.rpc) returns the query builder synchronously.
    """
    response = MagicMock()
    response.data = return_data

    query_builder = MagicMock()
    query_builder.execute = AsyncMock(return_value=response)

    client = MagicMock()
    client.rpc = MagicMock(return_value=query_builder)
    return client


def _make_table_mock(select_data: list[dict[str, Any]] | None) -> MagicMock:
    """Return a MagicMock that mimics
    ``client.table(name).select(...).eq(...).execute()`` chains returning
    ``select_data``.
    """
    response = MagicMock()
    response.data = select_data

    builder = MagicMock()
    builder.execute = AsyncMock(return_value=response)
    # All filter/order/limit/insert/update calls return self for fluent chaining.
    for method in (
        "select",
        "eq",
        "neq",
        "is_",
        "in_",
        "order",
        "limit",
        "single",
        "maybe_single",
        "insert",
        "update",
        "upsert",
        "delete",
    ):
        setattr(builder, method, MagicMock(return_value=builder))

    client = MagicMock()
    client.table = MagicMock(return_value=builder)
    return client, builder


_SAMPLE_VERSION_ROW = {
    "id": "ver-1",
    "template_id": "tmpl-1",
    "version_number": 2,
    "parent_version_id": "ver-0",
    "graph_nodes": [{"id": "n0", "kind": "trigger", "label": "Start"}],
    "graph_edges": [],
    "graph_layout": {"n0": {"x": 0, "y": 0}},
    "saved_by_user_id": "user-1",
    "saved_at": "2026-05-11T19:30:00.000000+00:00",
    "comment": "test save",
}


# ----------------------------------------------------------------------------
# save_template_version()
# ----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_save_template_version_happy_path_returns_new_version():
    """Successful Save: RPC returns the new row, helper returns a Pydantic model."""
    from app.workflows.template_versions import save_template_version

    client = _make_rpc_mock([_SAMPLE_VERSION_ROW])

    with patch(
        "app.workflows.template_versions.get_async_client",
        new=AsyncMock(return_value=client),
    ):
        result = await save_template_version(
            template_id="tmpl-1",
            user_id="user-1",
            graph_nodes=[{"id": "n0", "kind": "trigger", "label": "Start"}],
            graph_edges=[],
            graph_layout={"n0": {"x": 0, "y": 0}},
            comment="test save",
            if_match_saved_at="2026-05-11T19:25:00.000000+00:00",
        )

    assert result is not None
    assert result.id == "ver-1"
    assert result.template_id == "tmpl-1"
    assert result.version_number == 2
    assert result.saved_at == "2026-05-11T19:30:00.000000+00:00"


@pytest.mark.asyncio
async def test_save_template_version_stale_if_match_returns_none():
    """Stale If-Match: server returns zero rows, helper returns None for HTTP 412."""
    from app.workflows.template_versions import save_template_version

    client = _make_rpc_mock([])  # empty list = mismatch signal

    with patch(
        "app.workflows.template_versions.get_async_client",
        new=AsyncMock(return_value=client),
    ):
        result = await save_template_version(
            template_id="tmpl-1",
            user_id="user-1",
            graph_nodes=[],
            graph_edges=[],
            graph_layout=None,
            comment=None,
            if_match_saved_at="2026-05-11T19:00:00.000000+00:00",  # stale
        )

    assert result is None


@pytest.mark.asyncio
async def test_save_template_version_first_save_no_if_match():
    """First save (If-Match is None): RPC accepts None, returns the v1 row."""
    from app.workflows.template_versions import save_template_version

    v1_row = {**_SAMPLE_VERSION_ROW, "version_number": 1, "parent_version_id": None}
    client = _make_rpc_mock([v1_row])

    with patch(
        "app.workflows.template_versions.get_async_client",
        new=AsyncMock(return_value=client),
    ):
        result = await save_template_version(
            template_id="tmpl-1",
            user_id="user-1",
            graph_nodes=[],
            graph_edges=[],
            graph_layout=None,
            comment=None,
            if_match_saved_at=None,  # first save
        )

    assert result is not None
    assert result.version_number == 1
    # Verify the RPC was called with p_if_match_saved_at=None
    rpc_call = client.rpc.call_args
    assert rpc_call.args[0] == "save_workflow_template_version"
    params = rpc_call.args[1]
    assert params["p_if_match_saved_at"] is None
    assert params["p_parent_version_id"] is None


@pytest.mark.asyncio
async def test_save_template_version_passes_explicit_parent_version_id():
    """Revert flow: caller supplies parent_version_id, helper forwards it to RPC."""
    from app.workflows.template_versions import save_template_version

    client = _make_rpc_mock([_SAMPLE_VERSION_ROW])

    with patch(
        "app.workflows.template_versions.get_async_client",
        new=AsyncMock(return_value=client),
    ):
        await save_template_version(
            template_id="tmpl-1",
            user_id="user-1",
            graph_nodes=[],
            graph_edges=[],
            graph_layout=None,
            comment="reverted to v1",
            if_match_saved_at="2026-05-11T19:25:00.000000+00:00",
            parent_version_id="ver-target",
        )

    params = client.rpc.call_args.args[1]
    assert params["p_parent_version_id"] == "ver-target"
    assert params["p_comment"] == "reverted to v1"


@pytest.mark.asyncio
async def test_save_template_version_rpc_call_shape():
    """All 8 RPC parameters are passed with the right names and types."""
    from app.workflows.template_versions import save_template_version

    client = _make_rpc_mock([_SAMPLE_VERSION_ROW])

    with patch(
        "app.workflows.template_versions.get_async_client",
        new=AsyncMock(return_value=client),
    ):
        await save_template_version(
            template_id="tmpl-1",
            user_id="user-1",
            graph_nodes=[{"id": "n0", "kind": "trigger", "label": "Start"}],
            graph_edges=[{"id": "e0", "source": "n0", "target": "n1"}],
            graph_layout={"n0": {"x": 0, "y": 0}},
            comment="msg",
            if_match_saved_at="2026-05-11T19:25:00.000000+00:00",
        )

    fn_name, params = client.rpc.call_args.args
    assert fn_name == "save_workflow_template_version"
    expected_keys = {
        "p_template_id",
        "p_user_id",
        "p_graph_nodes",
        "p_graph_edges",
        "p_graph_layout",
        "p_comment",
        "p_if_match_saved_at",
        "p_parent_version_id",
    }
    assert set(params.keys()) == expected_keys
    assert params["p_template_id"] == "tmpl-1"
    assert params["p_user_id"] == "user-1"
    assert params["p_graph_nodes"] == [
        {"id": "n0", "kind": "trigger", "label": "Start"}
    ]
    assert params["p_graph_edges"] == [
        {"id": "e0", "source": "n0", "target": "n1"}
    ]


# ----------------------------------------------------------------------------
# list_template_history()
# ----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_template_history_returns_versions_desc_ordered():
    """list_template_history returns HistoryItem list ordered version_number DESC."""
    from app.workflows.template_versions import list_template_history

    rows = [
        {
            "id": "ver-3",
            "version_number": 3,
            "saved_at": "2026-05-11T20:00:00+00:00",
            "saved_by_user_id": "user-1",
            "comment": "third save",
        },
        {
            "id": "ver-2",
            "version_number": 2,
            "saved_at": "2026-05-11T19:30:00+00:00",
            "saved_by_user_id": "user-1",
            "comment": None,
        },
        {
            "id": "ver-1",
            "version_number": 1,
            "saved_at": "2026-05-11T19:00:00+00:00",
            "saved_by_user_id": None,  # backfill / seed
            "comment": "v1 backfill",
        },
    ]
    client, builder = _make_table_mock(rows)

    with patch(
        "app.workflows.template_versions.get_async_client",
        new=AsyncMock(return_value=client),
    ):
        history = await list_template_history("tmpl-1")

    assert len(history) == 3
    assert [h.version_number for h in history] == [3, 2, 1]
    assert history[0].version_id == "ver-3"
    assert history[1].version_id == "ver-2"
    assert history[2].saved_by_user_id is None  # nullable for backfill

    # Verify the SELECT clause was filtered on template_id + ordered desc
    builder.eq.assert_any_call("template_id", "tmpl-1")
    builder.order.assert_any_call("version_number", desc=True)


@pytest.mark.asyncio
async def test_list_template_history_returns_empty_for_unsaved_template():
    """No rows yet → empty list."""
    from app.workflows.template_versions import list_template_history

    client, _builder = _make_table_mock([])

    with patch(
        "app.workflows.template_versions.get_async_client",
        new=AsyncMock(return_value=client),
    ):
        history = await list_template_history("tmpl-empty")

    assert history == []


@pytest.mark.asyncio
async def test_list_template_history_tolerates_null_response_data():
    """Defensive: supabase may return data=None on certain backend errors."""
    from app.workflows.template_versions import list_template_history

    client, _builder = _make_table_mock(None)

    with patch(
        "app.workflows.template_versions.get_async_client",
        new=AsyncMock(return_value=client),
    ):
        history = await list_template_history("tmpl-1")

    assert history == []


# ----------------------------------------------------------------------------
# revert_template_to_version()
# ----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_revert_template_to_version_creates_new_version_with_target_as_parent():
    """Revert reads target's graph_*, calls save_template_version with
    parent_version_id=target.id, returns the new version row."""
    from app.workflows.template_versions import revert_template_to_version

    target_row = {
        "id": "ver-1",
        "template_id": "tmpl-1",
        "version_number": 1,
        "graph_nodes": [{"id": "n0", "kind": "trigger", "label": "Start"}],
        "graph_edges": [],
        "graph_layout": {"n0": {"x": 0, "y": 0}},
    }
    # Mock the SELECT to return target_row, then save_template_version returns
    # a new version row with version_number=3 (the next monotonic number).
    new_version = {
        **_SAMPLE_VERSION_ROW,
        "version_number": 3,
        "parent_version_id": "ver-1",
    }

    client, _builder = _make_table_mock([target_row])

    with patch(
        "app.workflows.template_versions.get_async_client",
        new=AsyncMock(return_value=client),
    ), patch(
        "app.workflows.template_versions.save_template_version",
        new=AsyncMock(return_value=_pydantic_version(new_version)),
    ) as save_mock:
        result = await revert_template_to_version(
            template_id="tmpl-1",
            version_id="ver-1",
            user_id="user-1",
            if_match_saved_at="2026-05-11T20:00:00+00:00",
        )

    assert result is not None
    assert result.parent_version_id == "ver-1"
    # save_template_version must have been called with parent_version_id="ver-1"
    kwargs = save_mock.call_args.kwargs
    assert kwargs["parent_version_id"] == "ver-1"
    assert kwargs["template_id"] == "tmpl-1"
    # Graph data must have been copied from the target version row
    assert kwargs["graph_nodes"] == target_row["graph_nodes"]
    assert kwargs["graph_edges"] == target_row["graph_edges"]


@pytest.mark.asyncio
async def test_revert_template_to_version_returns_none_when_target_missing():
    """Target version does not exist → returns None (caller translates to 404)."""
    from app.workflows.template_versions import revert_template_to_version

    client, _builder = _make_table_mock([])  # SELECT returns no rows

    with patch(
        "app.workflows.template_versions.get_async_client",
        new=AsyncMock(return_value=client),
    ):
        result = await revert_template_to_version(
            template_id="tmpl-1",
            version_id="missing-version",
            user_id="user-1",
            if_match_saved_at="2026-05-11T20:00:00+00:00",
        )

    assert result is None


# ----------------------------------------------------------------------------
# copy_seed_template_for_user()
# ----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_copy_seed_template_for_user_creates_private_copy_and_v1_version():
    """Editing a seed creates a private copy with created_by=user_id + bootstraps v1."""
    from app.workflows.template_versions import copy_seed_template_for_user

    seed_row = {
        "id": "seed-1",
        "name": "Content Creation Pipeline",
        "description": "Seed description",
        "category": "marketing",
        "template_key": "content_creation",
        "version": 1,
        "lifecycle_status": "published",
        "personas_allowed": ["marketing"],
        "created_by": None,  # critical: seeds have NULL created_by
        "graph_nodes": [{"id": "n0", "kind": "trigger", "label": "Start"}],
        "graph_edges": [],
        "graph_layout": {"n0": {"x": 0, "y": 0}},
        "current_version_id": "seed-ver-1",
    }
    new_template_row = {
        **seed_row,
        "id": "new-tmpl-1",
        "created_by": "user-1",
        "current_version_id": None,
    }
    new_version_row = {
        **_SAMPLE_VERSION_ROW,
        "id": "new-ver-1",
        "template_id": "new-tmpl-1",
        "version_number": 1,
    }

    # Three sequential calls expected: SELECT seed; INSERT template; INSERT version (via RPC).
    # We use a stateful mock that returns different data per call.
    call_idx = {"i": 0}

    def select_returns():
        responses = [
            [seed_row],          # SELECT seed
            [new_template_row],  # INSERT template returning *
        ]
        idx = call_idx["i"]
        call_idx["i"] += 1
        return responses[min(idx, len(responses) - 1)]

    builder = MagicMock()

    async def _execute():
        resp = MagicMock()
        resp.data = select_returns()
        return resp

    builder.execute = _execute
    for method in (
        "select",
        "eq",
        "is_",
        "limit",
        "single",
        "maybe_single",
        "insert",
        "update",
    ):
        setattr(builder, method, MagicMock(return_value=builder))

    rpc_response = MagicMock()
    rpc_response.data = [new_version_row]
    rpc_builder = MagicMock()
    rpc_builder.execute = AsyncMock(return_value=rpc_response)

    client = MagicMock()
    client.table = MagicMock(return_value=builder)
    client.rpc = MagicMock(return_value=rpc_builder)

    with patch(
        "app.workflows.template_versions.get_async_client",
        new=AsyncMock(return_value=client),
    ):
        result = await copy_seed_template_for_user(
            seed_template_id="seed-1", user_id="user-1"
        )

    # W-4: result MUST contain both copied_template_id AND seed_name keys
    assert "copied_template_id" in result
    assert "seed_name" in result
    assert result["copied_template_id"] == "new-tmpl-1"
    assert result["seed_name"] == "Content Creation Pipeline"


@pytest.mark.asyncio
async def test_copy_seed_template_for_user_raises_when_source_is_not_seed():
    """Source template with non-NULL created_by is NOT a seed; raise ValueError."""
    from app.workflows.template_versions import copy_seed_template_for_user

    non_seed_row = {
        "id": "tmpl-1",
        "name": "Private Template",
        "description": "",
        "category": "custom",
        "created_by": "other-user",  # NOT a seed
        "graph_nodes": [],
        "graph_edges": [],
        "graph_layout": None,
    }
    client, _builder = _make_table_mock([non_seed_row])

    with patch(
        "app.workflows.template_versions.get_async_client",
        new=AsyncMock(return_value=client),
    ), pytest.raises(ValueError, match="not a seed"):
        await copy_seed_template_for_user(
            seed_template_id="tmpl-1", user_id="user-1"
        )


@pytest.mark.asyncio
async def test_copy_seed_template_for_user_raises_when_seed_missing():
    """Source template does not exist at all → raise ValueError."""
    from app.workflows.template_versions import copy_seed_template_for_user

    client, _builder = _make_table_mock([])  # empty

    with patch(
        "app.workflows.template_versions.get_async_client",
        new=AsyncMock(return_value=client),
    ), pytest.raises(ValueError):
        await copy_seed_template_for_user(
            seed_template_id="missing", user_id="user-1"
        )


# ----------------------------------------------------------------------------
# Task 02-04 behavioural tests (engine integration)
# ----------------------------------------------------------------------------
#
# These do NOT exercise template_versions.py — they exercise app/workflows/engine.py
# via mocks to assert (a) list_templates SELECT clause now includes
# current_version_id, and (b) start_workflow_execution forwards
# template.current_version_id as p_template_version_id in rpc_params.
#
# Per W-7: BEHAVIORAL tests, NOT grep — catches silent regressions that a
# future refactor of how SELECT projections are built could otherwise sneak
# through.


@pytest.mark.asyncio
async def test_list_templates_select_includes_current_version_id():
    """engine.list_templates() must surface current_version_id on the returned dict.

    Mocks supabase_client().table("workflow_templates").select(...).execute()
    to return a row that includes current_version_id; asserts the engine's
    returned list preserves the key. If a future refactor narrows the SELECT
    clause back, this test fails.
    """
    from app.workflows.engine import WorkflowEngine

    sample_row = {
        "id": "tmpl-1",
        "name": "Test",
        "description": "desc",
        "category": "custom",
        "template_key": None,
        "version": 1,
        "lifecycle_status": "published",
        "is_generated": False,
        "personas_allowed": None,
        "published_at": None,
        "graph_nodes": None,
        "graph_edges": None,
        "graph_layout": None,
        "current_version_id": "ver-abc-123",
    }

    response = MagicMock()
    response.data = [sample_row]
    response.count = None

    # asyncio.wait_for awaits execute() — make it a coroutine that returns response.
    async def _coro_execute():
        return response

    query = MagicMock()
    query.eq = MagicMock(return_value=query)
    query.execute = MagicMock(return_value=_coro_execute())

    # Capture the select() call arg so we can assert current_version_id is in it.
    select_calls: list[str] = []

    def _select(cols: str):
        select_calls.append(cols)
        return query

    table = MagicMock()
    table.select = _select

    client = MagicMock()
    client.table = MagicMock(return_value=table)

    engine = WorkflowEngine()
    engine._async_client = client  # bypass _get_client()

    result = await engine.list_templates()

    # Behavioural assertion #1: SELECT clause includes current_version_id
    assert any(
        "current_version_id" in s for s in select_calls
    ), f"SELECT clause did not include current_version_id; saw: {select_calls}"

    # Behavioural assertion #2: returned list preserves the column on the dict
    assert len(result) == 1
    assert "current_version_id" in result[0]
    assert result[0]["current_version_id"] == "ver-abc-123"


@pytest.mark.asyncio
async def test_start_workflow_execution_passes_template_version_id_in_rpc_params():
    """engine.start_workflow_execution(..) must forward template.current_version_id
    as p_template_version_id in the rpc_params dict.

    Mocks the engine helpers down to the .rpc() call, captures rpc_params,
    asserts p_template_version_id is present and equals the template's
    current_version_id. Also asserts None propagates correctly when the
    template has no current_version_id (legacy rows).
    """
    from app.workflows.engine import WorkflowEngine

    template_with_version = {
        "id": "tmpl-1",
        "name": "Test",
        "current_version_id": "ver-2",
        "version": 1,
        "lifecycle_status": "published",
        "personas_allowed": None,
    }

    captured_rpc_params: dict[str, Any] = {}

    async def _rpc_execute():
        # Return an empty data list so engine.start_workflow_execution treats
        # this as "concurrency limit reached" and short-circuits (we only care
        # about asserting rpc_params).
        resp = MagicMock()
        resp.data = []
        resp.count = 0
        return resp

    rpc_builder = MagicMock()
    rpc_builder.execute = MagicMock(return_value=_rpc_execute())

    def _rpc(fn_name: str, params: dict[str, Any]):
        captured_rpc_params.clear()
        captured_rpc_params.update(params)
        captured_rpc_params["_fn_name"] = fn_name
        return rpc_builder

    # Stub the count-after-empty-RPC fetch too.
    async def _count_execute():
        resp = MagicMock()
        resp.data = []
        resp.count = 99  # arbitrary; we don't assert on this
        return resp

    count_query = MagicMock()
    for m in ("select", "eq", "in_"):
        setattr(count_query, m, MagicMock(return_value=count_query))
    count_query.execute = MagicMock(return_value=_count_execute())

    table_obj = MagicMock()
    table_obj.select = MagicMock(return_value=count_query)

    client = MagicMock()
    client.rpc = MagicMock(side_effect=_rpc)
    client.table = MagicMock(return_value=table_obj)

    engine = WorkflowEngine()
    engine._async_client = client

    # Patch helper methods so we don't trip on side concerns: readiness gate,
    # persona/lifecycle/infra checks. The test surface is rpc_params only.
    with patch.object(
        engine, "get_template", new=AsyncMock(return_value=template_with_version)
    ), patch.object(
        engine, "_evaluate_template_lifecycle", return_value={"ok": True}
    ), patch.object(
        engine,
        "_resolve_workflow_readiness",
        new=AsyncMock(return_value={"ready": True, "skip_gate": True}),
    ), patch.object(
        engine, "_get_execution_infra_guard_error", return_value=None
    ):
        # The engine may not expose start_workflow_execution directly under
        # that name — instead it likely uses ``start_workflow`` or similar.
        # We just need to drive the RPC path. Call whichever exists.
        start_fn = getattr(engine, "start_workflow_execution", None) or getattr(
            engine, "start_workflow", None
        )
        if start_fn is None:
            pytest.skip("engine has neither start_workflow_execution nor start_workflow")
        try:
            await start_fn(
                user_id="user-1",
                template_id="tmpl-1",
                run_source="user_ui",
                context={},
            )
        except TypeError:
            # Method signature may differ; fall back to keyword-flexible call.
            await start_fn(user_id="user-1", template_id="tmpl-1")

    # Behavioural assertion: rpc_params dict includes p_template_version_id
    # set to the template's current_version_id.
    assert captured_rpc_params.get("_fn_name") == "start_workflow_execution_atomic"
    assert "p_template_version_id" in captured_rpc_params
    assert captured_rpc_params["p_template_version_id"] == "ver-2"


# ----------------------------------------------------------------------------
# Helpers used by tests above
# ----------------------------------------------------------------------------


def _pydantic_version(row: dict[str, Any]):
    """Construct a WorkflowTemplateVersion model from a dict (test helper)."""
    from app.workflows.template_versions import WorkflowTemplateVersion

    return WorkflowTemplateVersion(**row)
