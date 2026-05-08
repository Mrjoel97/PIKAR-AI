# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Guard against widget-tool hallucinations in the Customer Support agent.

The agent's instruction must only reference widget tools that actually exist
in `app.agents.tools.ui_widgets`. Otherwise the LLM will silently call a
non-existent tool and the user sees no rendered widget.
"""

from __future__ import annotations

from app.agents.customer_support.agent import CUSTOMER_SUPPORT_AGENT_INSTRUCTION
from app.agents.tools import ui_widgets


def test_create_stat_widget_is_only_referenced_if_it_exists() -> None:
    """`create_stat_widget` must only appear in the prompt if implemented.

    If a future change adds a real `create_stat_widget` function to
    `ui_widgets.py`, the instruction is free to reference it again. Until then,
    the literal string must not appear in the system prompt.
    """
    referenced_in_prompt = "create_stat_widget" in CUSTOMER_SUPPORT_AGENT_INSTRUCTION
    exists_in_module = hasattr(ui_widgets, "create_stat_widget")

    if referenced_in_prompt:
        assert exists_in_module, (
            "Customer Support agent instruction references `create_stat_widget`, "
            "but no such function exists in app.agents.tools.ui_widgets. "
            "Either add the function or remove the reference from the prompt."
        )
    else:
        # Prompt does not reference it — that's fine regardless of module state.
        assert True
