from pydantic import BaseModel
import pytest

from app.workflows.execution_contracts import WorkflowContractError, build_tool_kwargs, verify_step_output


class _SearchInput(BaseModel):
    query: str


async def _search_tool(query: str):
    return {"success": True, "results": [{"query": query}]}


_search_tool.input_schema = _SearchInput


def test_build_tool_kwargs_uses_input_bindings_and_schema():
    kwargs = build_tool_kwargs(
        _search_tool,
        "mcp_web_search",
        {"topic": "market sizing"},
        step_name="Research",
        step_definition={"input_bindings": {"query": "topic"}},
        run_source="user_ui",
    )
    assert kwargs == {"query": "market sizing"}


def test_build_tool_kwargs_rejects_user_visible_missing_schema():
    async def _loose_tool(description: str):
        return {"success": True}

    with pytest.raises(WorkflowContractError) as exc:
        build_tool_kwargs(
            _loose_tool,
            "create_task",
            {"description": "Do something"},
            step_name="Loose",
            step_definition={"input_bindings": {"description": "description"}},
            run_source="user_ui",
        )

    assert exc.value.reason_code == "missing_schema"


def test_verify_step_output_flags_missing_expected_outputs():
    verification = verify_step_output(
        {"success": True},
        step_definition={
            "expected_outputs": ["page_id"],
            "verification_checks": ["success"],
        },
    )
    assert verification["status"] == "failed"
