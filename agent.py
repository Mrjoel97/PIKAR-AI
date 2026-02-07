# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""ADK Agent Discovery Entry Point.

This file re-exports the root_agent for ADK CLI discovery.
When running `adk run .` or `adk web .`, ADK looks for a root_agent
in the top-level agent.py file.

NOTE: We export the Agent instance directly, not the App wrapper,
because ADK's path resolution uses the agent's module location
to determine the app_name, and the App wrapper confuses this.
"""

from app.agent import executive_agent

# ADK CLI expects this variable name for agent discovery
root_agent = executive_agent
