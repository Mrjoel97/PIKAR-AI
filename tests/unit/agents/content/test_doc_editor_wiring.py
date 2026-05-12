"""Verify DOCUMENT_EDITOR_TOOLS + INSTRUCTION are wired into ContentCreationAgent.

Post W4-Pilot, content uses a :class:`~app.agents.runtime.tools_manifest.ToolsManifest`
whose resolved entries include :class:`_ToolPack` wrappers (e.g. for the
``document_editor`` pack). Tests flatten the packs before asserting on
individual tool names so the assertion's intent — that every doc-editor
tool is reachable — keeps holding through the migration.
"""

from unittest.mock import patch
from uuid import uuid4


def _flatten_agent_tools(agent):
    """Return the flat set of callable tool names on the agent.

    ``agent.tools`` may contain ``_ToolPack`` wrappers (post-W4) which
    expose their underlying callables on ``.tools``. Flatten one level so
    the doc-editor functions surface even when packed.
    """
    names: set[str] = set()
    for tool in agent.tools:
        pack_tools = getattr(tool, "tools", None)
        if isinstance(pack_tools, list):
            for inner in pack_tools:
                inner_name = getattr(inner, "__name__", None) or getattr(
                    inner, "name", ""
                )
                if inner_name:
                    names.add(inner_name)
            continue
        name = getattr(tool, "__name__", None) or getattr(tool, "name", "")
        if name:
            names.add(name)
    return names


def test_content_agent_has_all_doc_editor_tools():
    """ContentCreationAgent.tools includes all 7 doc-editor tools."""
    from app.agents.content.agent import create_content_agent

    with patch("app.agents.base_agent.PikarAgent.__init__", return_value=None):
        agent = create_content_agent(user_id=uuid4(), persona_id="startup")
    # PikarBaseAgent stores the resolved tools list on ``_tools_manifest``
    # after construction; when the parent ``__init__`` is patched out, the
    # ADK-side ``self.tools`` attribute is never populated, so we resolve
    # via the manifest directly.
    resolved = agent._tools_manifest.resolve()
    tool_names: set[str] = set()
    for tool in resolved:
        pack_tools = getattr(tool, "tools", None)
        if isinstance(pack_tools, list):
            for inner in pack_tools:
                inner_name = getattr(inner, "__name__", None) or getattr(
                    inner, "name", ""
                )
                if inner_name:
                    tool_names.add(inner_name)
            continue
        name = getattr(tool, "__name__", None) or getattr(tool, "name", "")
        if name:
            tool_names.add(name)
    expected = {
        "read_document_content",
        "edit_report_doc",
        "edit_spreadsheet",
        "edit_presentation",
        "edit_word_doc",
        "edit_google_doc",
        "list_document_versions",
    }
    missing = expected - tool_names
    assert not missing, f"ContentCreationAgent missing doc-editor tools: {missing}"


def test_content_agent_instruction_mentions_doc_editor_workflow():
    """Agent's instruction.md contains the doc-editor workflow guidance."""
    from pathlib import Path

    instructions_path = (
        Path(__file__).resolve().parents[4]
        / "app"
        / "agents"
        / "content"
        / "instructions.md"
    )
    body = instructions_path.read_text(encoding="utf-8")
    assert "read_document_content" in body
    assert "edit_report_doc" in body
    assert "Editing Documents" in body
