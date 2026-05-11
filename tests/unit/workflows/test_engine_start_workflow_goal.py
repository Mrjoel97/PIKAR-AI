"""Verify start_workflow persists goal and emits workspace_item."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.workflows.engine import WorkflowEngine


def _make_fake_client(fake_execution: dict) -> MagicMock:
    """Build a mock Supabase client that:
    - Returns a published template row on .table("workflow_templates").select().eq().limit().execute()
    - Returns the fake execution on .rpc(...).execute()
    - Returns an empty active-count result for any other table call
    """
    fake_template = {
        "id": "t1",
        "name": "Plan",
        "phases": [],
        "lifecycle_status": "published",
        "version": 1,
        "personas_allowed": None,
        "is_generated": False,
        "template_key": "plan",
    }

    # Template query chain
    template_res = MagicMock()
    template_res.data = [fake_template]
    template_query = MagicMock()
    template_query.select.return_value = template_query
    template_query.eq.return_value = template_query
    template_query.limit.return_value = template_query
    template_query.execute = AsyncMock(return_value=template_res)

    # RPC chain — returns the fake execution row
    exec_res = MagicMock()
    exec_res.data = [fake_execution]
    rpc_chain = MagicMock()
    rpc_chain.execute = AsyncMock(return_value=exec_res)

    # Audit insert chain (swallow silently)
    audit_res = MagicMock()
    audit_res.data = [{}]
    audit_chain = MagicMock()
    audit_chain.insert.return_value = audit_chain
    audit_chain.execute = AsyncMock(return_value=audit_res)

    def _table_router(table_name: str) -> MagicMock:
        if table_name == "workflow_templates":
            return template_query
        # workflow_execution_audit or workflow_readiness_checks → swallow
        return audit_chain

    client = MagicMock()
    client.table.side_effect = _table_router
    client.rpc.return_value = rpc_chain
    return client


@pytest.mark.asyncio
async def test_start_workflow_persists_goal_and_emits_workspace_item():
    fake_execution = {
        "id": "exec-1",
        "user_id": "u-1",
        "name": "Plan - 2026-05-11 13:01",
        "goal": "ship Q3",
    }
    fake_client = _make_fake_client(fake_execution)
    fake_emit = AsyncMock()

    with patch(
        "app.workflows.engine.WorkspaceItemEmitter",
        return_value=MagicMock(emit_for_execution=fake_emit),
    ), patch.object(
        WorkflowEngine,
        "_get_client",
        new=AsyncMock(return_value=fake_client),
    ), patch.object(
        WorkflowEngine,
        "_resolve_workflow_persona",
        new=AsyncMock(return_value="ceo"),
    ), patch(
        "app.workflows.engine.edge_function_client.execute_workflow",
        new=AsyncMock(return_value={"status": "ok"}),
    ), patch(
        "app.workflows.engine.WorkflowEngine._get_workflow_readiness",
        new=AsyncMock(return_value={"status": "ready"}),
    ), patch(
        "app.workflows.engine.WorkflowEngine._is_readiness_gate_enabled",
        return_value=False,
    ), patch(
        "app.workflows.engine.WorkflowEngine._get_execution_infra_guard_error",
        return_value=None,
    ), patch(
        "app.workflows.engine.WorkflowEngine._is_user_visible_run_source",
        return_value=True,
    ), patch(
        "app.workflows.engine.WorkflowEngine._audit_execution_action",
        new=AsyncMock(return_value=None),
    ), patch(
        "app.workflows.engine.normalize_template_for_execution",
        side_effect=lambda t, **kw: t,
    ), patch(
        "app.workflows.engine.validate_template_phases",
        return_value=[],
    ):
        engine = WorkflowEngine()
        result = await engine.start_workflow(
            user_id="u-1",
            template_name="Plan",
            goal="ship Q3",
            run_source="user_ui",
        )

    # Verify the RPC was called with p_goal
    rpc_call_args = fake_client.rpc.call_args
    assert rpc_call_args is not None, "rpc() was never called"
    rpc_name = rpc_call_args.args[0] if rpc_call_args.args else rpc_call_args[0][0]
    assert rpc_name == "start_workflow_execution_atomic"
    rpc_params = rpc_call_args.args[1] if len(rpc_call_args.args) > 1 else rpc_call_args[0][1]
    assert rpc_params.get("p_goal") == "ship Q3", f"p_goal missing from RPC params: {rpc_params}"

    # Verify emitter was awaited with the execution and run_source
    fake_emit.assert_awaited_once()
    call_kwargs = fake_emit.call_args.kwargs
    assert call_kwargs["run_source"] == "user_ui"

    # Verify result shape
    assert result.get("execution_id") == "exec-1"


@pytest.mark.asyncio
async def test_emitter_not_called_when_flag_disabled():
    """When LIVE_WORKFLOW_VIEW=False the workspace_item emitter is skipped."""
    fake_execution = {
        "id": "exec-1",
        "user_id": "u-1",
        "name": "Plan - 2026-05-11 13:01",
        "goal": "ship",
    }
    fake_client = _make_fake_client(fake_execution)
    fake_emit = AsyncMock()

    with patch(
        "app.workflows.engine.WorkspaceItemEmitter",
        return_value=MagicMock(emit_for_execution=fake_emit),
    ), patch(
        "app.workflows.engine.LIVE_WORKFLOW_VIEW",
        False,
    ), patch.object(
        WorkflowEngine,
        "_get_client",
        new=AsyncMock(return_value=fake_client),
    ), patch.object(
        WorkflowEngine,
        "_resolve_workflow_persona",
        new=AsyncMock(return_value="ceo"),
    ), patch(
        "app.workflows.engine.edge_function_client.execute_workflow",
        new=AsyncMock(return_value={"status": "ok"}),
    ), patch(
        "app.workflows.engine.WorkflowEngine._get_workflow_readiness",
        new=AsyncMock(return_value={"status": "ready"}),
    ), patch(
        "app.workflows.engine.WorkflowEngine._is_readiness_gate_enabled",
        return_value=False,
    ), patch(
        "app.workflows.engine.WorkflowEngine._get_execution_infra_guard_error",
        return_value=None,
    ), patch(
        "app.workflows.engine.WorkflowEngine._is_user_visible_run_source",
        return_value=True,
    ), patch(
        "app.workflows.engine.WorkflowEngine._audit_execution_action",
        new=AsyncMock(return_value=None),
    ), patch(
        "app.workflows.engine.normalize_template_for_execution",
        side_effect=lambda t, **kw: t,
    ), patch(
        "app.workflows.engine.validate_template_phases",
        return_value=[],
    ):
        engine = WorkflowEngine()
        result = await engine.start_workflow(
            user_id="u-1",
            template_name="Plan",
            goal="ship",
            run_source="user_ui",
        )

    fake_emit.assert_not_awaited()
    assert result.get("execution_id") == "exec-1"
