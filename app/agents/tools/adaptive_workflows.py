# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0
#
# Portions copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Adaptive Workflow Tools.

Tools for the Strategic Agent to design new processes.
"""

import asyncio
from typing import Any


def generate_workflow_template(
    user_id: str, goal: str, context: str = ""
) -> dict[str, Any]:
    """Design and save a new workflow template based on a goal.

    Use this when the user asks to "create a process", "design a workflow",
    or "how should we handle X".

    Args:
        user_id: User context ID.
        goal: Description of what the workflow should achieve (e.g. "Onboard new enterprise clients").
        context: Additional business context (e.g. "We need legal review and API provisioning").

    Returns:
        Details of the created template.
    """
    # Lazy import to avoid circular dependency:
    # agents -> adaptive_workflows -> workflows -> initiative -> specialized_agents -> agents
    from app.workflows.generator import get_workflow_generator

    generator = get_workflow_generator()
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    return loop.run_until_complete(generator.generate_workflow(user_id, goal, context))


ADAPTIVE_TOOLS = [generate_workflow_template]
