"""Regression test for QUALITY-10: ensure unsafe exec/path tools stay removed.

`run_script` and `update_code` were removed from
`app/agents/tools/integration_tools.py` because they accepted unsanitized
inputs (raw script bodies, arbitrary file paths) without sandboxing,
allowlists, or path-traversal guards. This test prevents accidental
reintroduction.
"""

from app.agents.tools import integration_tools


def test_run_script_is_not_exposed():
    """`run_script` must not be importable from integration_tools."""
    assert getattr(integration_tools, "run_script", None) is None, (
        "run_script was reintroduced to integration_tools without a sandbox; "
        "see QUALITY-10."
    )


def test_update_code_is_not_exposed():
    """`update_code` must not be importable from integration_tools."""
    assert getattr(integration_tools, "update_code", None) is None, (
        "update_code was reintroduced to integration_tools without a "
        "path-traversal guard; see QUALITY-10."
    )
