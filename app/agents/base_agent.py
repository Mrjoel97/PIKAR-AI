# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Custom Agent wrapper to fix ADK path resolution.

ADK uses inspect.getfile() on the Agent class to determine app_name.
By subclassing Agent here, the class definition is in the user's project,
allowing ADK to correctly infer the app name from the directory.
"""

from google.adk.agents import Agent as BaseAgent


class PikarAgent(BaseAgent):
    """Custom Agent subclass for Pikar AI.

    This exists solely to fix ADK's path resolution issue.
    The class must be defined in the user's project (not google.adk.agents)
    for ADK to correctly infer the app name from the directory structure.
    """

    pass
