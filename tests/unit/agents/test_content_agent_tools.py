"""HYGIENE-03: ContentCreationAgent has direct access to SOCIAL_TOOLS.

Verifies plan 108-03: ContentCreationAgent can publish to social platforms
without delegating to MarketingAutomationAgent's SocialMedia sub-agent. The
underlying tool functions are stateless and module-level, so both agents may
share the same callables.

Post W4-Pilot the director's tool surface is built from a
:class:`ToolsManifest`; the social tools live inside a ``_ToolPack``
wrapper resolved against ``app.agents.tools.social``. The helper flattens
packs so the assertion's intent (per-function presence) is preserved.
"""

from unittest.mock import patch
from uuid import uuid4


def _tool_names(tools):
    """Extract a set of tool names from a list of ADK tools or callables."""
    names = set()
    for t in tools:
        name = getattr(t, "__name__", None) or getattr(t, "name", None)
        if name:
            names.add(name)
    return names


def _resolved_director_tool_names() -> set[str]:
    """Build a content director under a patched ADK parent and flatten the
    resolved manifest down to individual callable names."""
    from app.agents.content.agent import create_content_agent

    with patch("app.agents.base_agent.PikarAgent.__init__", return_value=None):
        agent = create_content_agent(user_id=uuid4(), persona_id="startup")
    resolved = agent._tools_manifest.resolve()
    names: set[str] = set()
    for tool in resolved:
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


def test_content_agent_has_social_tools():
    """ContentCreationAgent's tools list contains all 4 SOCIAL_TOOLS functions."""
    tool_names = _resolved_director_tool_names()

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
    """instructions.md mentions direct social posting capability (post-W4 the
    instruction is loaded from disk by ``PikarBaseAgent``)."""
    from pathlib import Path

    instructions_path = (
        Path(__file__).resolve().parents[3]
        / "app"
        / "agents"
        / "content"
        / "instructions.md"
    )
    body = instructions_path.read_text(encoding="utf-8")
    assert "DIRECT SOCIAL POSTING" in body, (
        "Expected 'DIRECT SOCIAL POSTING' subsection in content/instructions.md"
    )
    # Each of the four social tool function names should be referenced in the prompt.
    assert "publish_to_social" in body
    assert "list_connected_accounts" in body
    assert "get_oauth_url" in body
    assert "disconnect_social_account" in body


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
