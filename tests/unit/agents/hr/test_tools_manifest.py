# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Contract test: the HR tool manifest resolves every tool to a real callable."""

from pathlib import Path

from app.agents.hr.tools import _TOOL_IDS, build_tools_manifest
from app.agents.runtime.operations_config import OperationsConfig
from app.agents.runtime.tools_manifest import ToolsManifest

OPS_PATH = (
    Path(__file__).resolve().parents[4]
    / "app"
    / "agents"
    / "hr"
    / "operations.yaml"
)


def test_manifest_returns_tools_manifest_instance():
    ops = OperationsConfig.load(OPS_PATH)
    manifest = build_tools_manifest(ops)
    assert isinstance(manifest, ToolsManifest)
    assert manifest.tool_ids


def test_manifest_includes_core_hr_tools():
    ops = OperationsConfig.load(OPS_PATH)
    manifest = build_tools_manifest(ops)
    for required in [
        "create_job",
        "get_job",
        "list_jobs",
        "add_candidate",
        "list_candidates",
        "generate_job_description",
        "generate_interview_questions",
        "get_hiring_funnel",
        "auto_generate_onboarding",
        "knowledge",
        "calendar_tool",
        "ui_widgets",
        "context_memory",
        "document_gen",
    ]:
        assert required in manifest.tool_ids, (
            f"manifest missing required tool: {required}"
        )


def test_manifest_resolves_every_id_to_a_callable():
    ops = OperationsConfig.load(OPS_PATH)
    manifest = build_tools_manifest(ops)
    resolved = manifest.resolve()
    assert len(resolved) == len(manifest.tool_ids)
    for tool in resolved:
        assert callable(tool), f"resolved entry is not callable: {tool!r}"


def test_tool_ids_constant_is_stable():
    assert isinstance(_TOOL_IDS, list)
    assert len(_TOOL_IDS) >= 15


def test_manifest_resolves_local_callables_first():
    from app.agents.hr.tools import (
        add_candidate,
        auto_generate_onboarding,
        create_job,
        generate_interview_questions,
        generate_job_description,
        get_hiring_funnel,
        list_candidates,
        list_jobs,
    )

    ops = OperationsConfig.load(OPS_PATH)
    manifest = build_tools_manifest(ops)
    resolved = manifest.resolve()
    by_id = dict(zip(manifest.tool_ids, resolved, strict=True))

    assert by_id["create_job"] is create_job
    assert by_id["list_jobs"] is list_jobs
    assert by_id["add_candidate"] is add_candidate
    assert by_id["list_candidates"] is list_candidates
    assert by_id["generate_job_description"] is generate_job_description
    assert by_id["generate_interview_questions"] is generate_interview_questions
    assert by_id["get_hiring_funnel"] is get_hiring_funnel
    assert by_id["auto_generate_onboarding"] is auto_generate_onboarding
