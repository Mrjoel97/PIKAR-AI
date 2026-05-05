"""Verify DOCUMENT_EDITOR_TOOLS + INSTRUCTION are wired into ContentCreationAgent."""


def test_content_agent_has_all_doc_editor_tools():
    """ContentCreationAgent.tools includes all 7 doc-editor tools."""
    from app.agents.content.agent import create_content_agent

    agent = create_content_agent()
    tool_names = {getattr(t, "__name__", getattr(t, "name", "")) for t in agent.tools}
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
    """Agent's instruction string contains the doc-editor workflow guidance."""
    from app.agents.content.agent import create_content_agent

    agent = create_content_agent()
    assert "read_document_content" in agent.instruction
    assert "edit_report_doc" in agent.instruction
    assert "Editing Documents" in agent.instruction
