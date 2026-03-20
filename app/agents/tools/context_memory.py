# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Context Memory Tools — Persistent fact storage for agent conversation memory.

These tools allow agents to save and retrieve key user-provided facts
(company name, industry, products, goals, etc.) to session.state so
they survive event pruning and compaction.

The saved context is also injected into agent prompts via the
{user_context} template variable, ensuring agents always have access
to critical user facts regardless of conversation length.
"""

import logging

logger = logging.getLogger(__name__)


def save_user_context(key: str, value: str) -> dict:
    """Save an important fact about the user or their business to memory.

    Use this whenever the user shares key information you'll need later,
    such as their company name, industry, product details, target audience,
    goals, preferences, or any important business context.

    This persists across the entire conversation so you never need to
    re-ask for this information.

    Args:
        key: A short descriptive label for the fact (e.g., 'company_name',
             'industry', 'target_audience', 'main_product', 'business_goal').
        value: The actual information to remember (e.g., 'TechNova',
               'B2B SaaS for HR departments').

    Returns:
        Confirmation that the fact was saved.
    """
    # The actual state persistence is handled by the ToolContext callback
    # in the after_tool_callback. Here we return the data for the callback.
    return {
        "_context_memory_save": True,
        "key": key,
        "value": value,
        "status": "saved",
        "message": f"Noted: {key} = {value}",
    }


def get_conversation_context() -> dict:
    """Retrieve all known facts about the user and their business.

    Call this at the start of complex tasks to refresh your memory
    of what the user has told you. This returns everything saved via
    save_user_context.

    Returns:
        Dictionary of all known user context facts.
    """
    # The actual state retrieval is handled by the ToolContext callback.
    return {
        "_context_memory_get": True,
        "message": "Context retrieval requested — see state injection.",
    }


# Tools list for export
CONTEXT_MEMORY_TOOLS = [
    save_user_context,
    get_conversation_context,
]
