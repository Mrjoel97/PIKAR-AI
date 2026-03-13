import importlib

import pytest

from app.workflows.execution_contracts import WorkflowContractError, build_tool_kwargs


async def _degraded_tool(**kwargs):
    return {"success": True}


_degraded_tool.__module__ = "app.agents.tools.degraded_tools"


def test_build_tool_kwargs_rejects_degraded_tool_in_production_even_for_background_runs(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")

    with pytest.raises(WorkflowContractError) as exc:
        build_tool_kwargs(
            _degraded_tool,
            "query_analytics",
            {"report_id": "rpt_123"},
            step_name="Analytics sync",
            run_source="system",
            tool_registry={"query_analytics": _degraded_tool},
        )

    assert exc.value.reason_code == "degraded_tool_not_allowed"
    assert "production execution" in str(exc.value)


def test_fastapi_cors_allows_persona_and_user_headers(monkeypatch):
    monkeypatch.setenv("LOCAL_DEV_BYPASS", "1")
    monkeypatch.setenv("SKIP_ENV_VALIDATION", "1")
    monkeypatch.setenv("ENVIRONMENT", "test")

    from app import fast_api_app

    importlib.reload(fast_api_app)

    headers = {header.lower() for header in fast_api_app._cors_allowed_headers}
    assert {"x-pikar-persona", "x-user-id", "user-id"}.issubset(headers)
