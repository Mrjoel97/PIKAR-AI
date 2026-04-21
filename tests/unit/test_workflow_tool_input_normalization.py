import pytest

from app.agents.tools.workflows import (
    _coerce_approval_args,
    _coerce_context_dict,
)


def test_coerce_context_dict_accepts_plain_string() -> None:
    assert _coerce_context_dict("launch plan") == {"context": "launch plan"}


def test_coerce_context_dict_accepts_json_object_string() -> None:
    assert _coerce_context_dict('{"goal":"launch","priority":"high"}') == {
        "goal": "launch",
        "priority": "high",
    }


def test_coerce_approval_args_extracts_execution_id_from_string_blob() -> None:
    execution_id, feedback = _coerce_approval_args(
        'execution_id: "5b179726-358b-4942-9891-3113799c0e30"',
        "",
    )

    assert execution_id == "5b179726-358b-4942-9891-3113799c0e30"
    assert feedback == ""


def test_coerce_approval_args_accepts_dict_payload() -> None:
    execution_id, feedback = _coerce_approval_args(
        {
            "execution_id": "5b179726-358b-4942-9891-3113799c0e30",
            "feedback": "Approved",
        },
        "",
    )

    assert execution_id == "5b179726-358b-4942-9891-3113799c0e30"
    assert feedback == "Approved"


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (None, {}),
        ("", {}),
        (["a", "b"], {"context": "['a', 'b']"}),
    ],
)
def test_coerce_context_dict_handles_non_mapping_inputs(raw, expected) -> None:
    assert _coerce_context_dict(raw) == expected
