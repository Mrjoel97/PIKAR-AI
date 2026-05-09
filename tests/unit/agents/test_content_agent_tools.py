"""HYGIENE-03: ContentCreationAgent has direct access to SOCIAL_TOOLS.

Verifies plan 108-03: ContentCreationAgent can publish to social platforms
without delegating to MarketingAutomationAgent's SocialMedia sub-agent. The
underlying tool functions are stateless and module-level, so both agents may
share the same callables.
"""


def _tool_names(tools):
    """Extract a set of tool names from a list of ADK tools or callables."""
    names = set()
    for t in tools:
        name = getattr(t, "__name__", None) or getattr(t, "name", None)
        if name:
            names.add(name)
    return names


def test_content_agent_has_social_tools():
    """ContentCreationAgent's tools list contains all 4 SOCIAL_TOOLS functions."""
    from app.agents.content.agent import create_content_agent

    agent = create_content_agent()
    tool_names = _tool_names(agent.tools)

    assert "publish_to_social" in tool_names, (
        f"Missing publish_to_social. Got: {sorted(tool_names)}"
    )
    assert "list_connected_accounts" in tool_names, (
        f"Missing list_connected_accounts. Got: {sorted(tool_names)}"
    )
    assert "get_oauth_url" in tool_names, (
        f"Missing get_oauth_url. Got: {sorted(tool_names)}"
    )
    assert "disconnect_social_account" in tool_names, (
        f"Missing disconnect_social_account. Got: {sorted(tool_names)}"
    )


def test_content_agent_instruction_mentions_direct_social_posting():
    """The CONTENT_DIRECTOR_INSTRUCTION mentions direct social posting capability."""
    from app.agents.content.agent import create_content_agent

    agent = create_content_agent()
    assert "DIRECT SOCIAL POSTING" in agent.instruction, (
        "Expected 'DIRECT SOCIAL POSTING' subsection in ContentCreationAgent's instruction"
    )
    # Each of the four social tool function names should be referenced in the prompt.
    assert "publish_to_social" in agent.instruction
    assert "list_connected_accounts" in agent.instruction
    assert "get_oauth_url" in agent.instruction
    assert "disconnect_social_account" in agent.instruction


def test_marketing_social_subagent_unchanged_regression():
    """Marketing's _SOCIAL_TOOLS_LIST still contains all 4 SOCIAL_TOOLS functions.

    Regression guardrail against accidental refactors that move SOCIAL_TOOLS
    out of the Marketing path. Both agents share the stateless callables.
    """
    from app.agents.marketing.agent import _SOCIAL_TOOLS_LIST
    from app.agents.tools.social import SOCIAL_TOOLS

    tool_names = _tool_names(_SOCIAL_TOOLS_LIST)

    for fn in SOCIAL_TOOLS:
        fn_name = getattr(fn, "__name__", None) or getattr(fn, "name", None)
        assert fn_name in tool_names, (
            f"Marketing _SOCIAL_TOOLS_LIST lost {fn_name}. Got: {sorted(tool_names)}"
        )
